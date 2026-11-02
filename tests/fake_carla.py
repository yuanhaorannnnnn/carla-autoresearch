"""Small stateful CARLA boundary fake, installed only by tests."""
import copy
import fnmatch
from types import SimpleNamespace


def placement(z=0):
    return SimpleNamespace(location=SimpleNamespace(x=1.0, y=2.0, z=z), rotation=SimpleNamespace(pitch=0.0, yaw=90.0, roll=0.0))


class Attribute:
    def __init__(self, name, value, modifiable=True):
        self.id, self.value, self.is_modifiable = name, value, modifiable
        self.recommended_values = []

    def __str__(self):
        return str(self.value)


class Blueprint:
    def __init__(self, name, attributes):
        self.id = name
        self.attributes = {key: Attribute(key, value) for key, value in attributes.items()}

    def __iter__(self):
        return iter(self.attributes.values())

    def has_attribute(self, key):
        return key in self.attributes

    def get_attribute(self, key):
        return self.attributes[key]

    def set_attribute(self, key, value):
        if key in ("image_size_x", "image_size_y", "channels") and int(value) <= 0:
            raise ValueError("must be positive")
        self.attributes[key].value = value


class Library:
    def __init__(self):
        self.items = {
            "vehicle.tesla.model3": Blueprint("vehicle.tesla.model3", {"role_name": ""}),
            "sensor.camera.rgb": Blueprint("sensor.camera.rgb", {"image_size_x": "2", "image_size_y": "1", "sensor_tick": "0", "role_name": "default"}),
            "sensor.lidar.ray_cast": Blueprint("sensor.lidar.ray_cast", {"channels": "16", "sensor_tick": "0", "role_name": "default"}),
        }

    def find(self, name):
        if name not in self.items:
            raise RuntimeError("unknown blueprint")
        return copy.deepcopy(self.items[name])

    def filter(self, pattern):
        return [self.find(name) for name in self.items if fnmatch.fnmatch(name, pattern)]


class Actors(list):
    def filter(self, pattern):
        return Actors(actor for actor in self if fnmatch.fnmatch(actor.type_id, pattern))


class Actor:
    def __init__(self, world, actor_id, blueprint, transform=None):
        self.world, self.id, self.type_id = world, actor_id, blueprint.id
        self.attributes = {attribute.id: str(attribute) for attribute in blueprint}
        self.is_listening, self.callback = False, None
        self.transform = transform or placement()
        self.simulate_physics = True
        self.velocity = SimpleNamespace(x=0.0, y=0.0, z=0.0)
        self.acceleration = SimpleNamespace(x=1.0, y=0.0, z=0.0)
        if self.type_id.startswith("vehicle."):
            self.bounding_box = placement()
            self.bounding_box.extent = SimpleNamespace(x=2.0, y=1.0, z=0.5)

    def apply_control(self, control):
        self.world.control_calls.append((self.id, copy.copy(control)))

    def get_velocity(self):
        return self.velocity

    def get_acceleration(self):
        return self.acceleration

    def set_simulate_physics(self, enabled):
        self.simulate_physics = enabled
        self.world.physics_calls.append((self.id, enabled))

    def get_transform(self):
        return self.transform

    def listen(self, callback):
        self.callback, self.is_listening = callback, True

    def stop(self):
        self.is_listening = False

    def destroy(self):
        if self.world.destroy_error:
            raise RuntimeError("destroy error")
        self.world.destroyed.append(self.id)
        del self.world.actors[self.id]
        return True

    def emit(self, frame):
        raw = b"\x00\x01\x02\xff" * 2 if self.type_id == "sensor.camera.rgb" else b"\x00" * 32
        self.callback(SimpleNamespace(frame=frame, timestamp=frame * 0.05, raw_data=raw, width=2, height=1))


class World:
    def __init__(self):
        self.id, self.frame, self.next_id = 42, 0, 1
        self.settings = SimpleNamespace(synchronous_mode=False, fixed_delta_seconds=None, no_rendering_mode=False)
        self.library, self.actors, self.destroyed = Library(), {}, []
        self.destroy_error, self.tick_error, self.no_frames = False, False, False
        self.out_of_order, self.duplicate, self.change_episode = False, False, False
        self.apply_error = False
        self.callback_delay_ticks = 0
        self.burst_frames = 0
        self.skip_sensor_until_frame = 0
        self.physics_calls = []
        self.tick_step = 1
        self.control_calls = []
        self.weather = SimpleNamespace(cloudiness=10.0, snow_precipitation=2.0,
                                       snow_accumulation=3.0, environment_lighting_gain=1.5)
        self.spectator_transform = placement(50.0)
        self.spawn_points = [placement(100.0)]

    def get_map(self):
        return SimpleNamespace(name="TownTest", get_spawn_points=lambda: self.spawn_points)

    def get_weather(self):
        return self.weather

    def get_spectator(self):
        return SimpleNamespace(get_transform=lambda: self.spectator_transform)

    def get_settings(self):
        return copy.copy(self.settings)

    def apply_settings(self, settings):
        self.settings = copy.copy(settings)
        if self.apply_error:
            self.apply_error = False
            raise RuntimeError("apply timeout after apply")
        return self.frame

    def get_blueprint_library(self):
        return self.library

    def get_actor(self, actor_id):
        return self.actors.get(actor_id)

    def get_actors(self):
        return Actors(self.actors.values())

    def try_spawn_actor(self, blueprint, transform):
        return self.spawn_actor(blueprint, transform)

    def spawn_actor(self, blueprint, transform, attach_to=None):
        actor = Actor(self, self.next_id, blueprint, transform)
        self.actors[actor.id] = actor
        self.next_id += 1
        return actor

    def get_snapshot(self):
        return SimpleNamespace(frame=self.frame, timestamp=SimpleNamespace(elapsed_seconds=self.frame * 0.05, delta_seconds=0.05, platform_timestamp=1.0))

    def tick(self, timeout):
        if self.tick_error:
            raise RuntimeError("tick timeout")
        self.frame += self.tick_step
        if self.change_episode:
            self.id += 1
        for actor in list(self.actors.values()):
            if actor.is_listening and not self.no_frames:
                for extra in range(self.burst_frames):
                    actor.emit(self.frame + extra)
                if self.out_of_order and self.frame == 1:
                    actor.emit(2)
                    actor.emit(0)
                emitted = self.frame - self.callback_delay_ticks
                if emitted > self.skip_sensor_until_frame and not (self.out_of_order and self.frame == 2):
                    actor.emit(emitted)
                if self.duplicate:
                    actor.emit(self.frame + 1)
                    actor.emit(self.frame + 1)
        return self.frame


def make_module(world):
    class VehicleControl:
        def __init__(self):
            self.throttle, self.steer, self.brake, self.gear = 0.0, 0.0, 0.0, 0
            self.hand_brake = self.reverse = self.manual_gear_shift = False

    class Client:
        def __init__(self, host, port):
            self.host, self.port = host, port

        def set_timeout(self, timeout):
            self.timeout = timeout

        def get_world(self):
            return world

        def get_server_version(self):
            return "sprint42"

        def get_client_version(self):
            return "sprint42"

    return SimpleNamespace(Client=Client, VehicleControl=VehicleControl, Location=lambda **kw: SimpleNamespace(**kw),
                           Rotation=lambda **kw: SimpleNamespace(**kw), Transform=lambda location, rotation: SimpleNamespace(location=location, rotation=rotation))
