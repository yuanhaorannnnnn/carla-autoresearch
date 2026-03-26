# Project Memory

Date: 2026-03-25
Module Context: `autoresearch` root training workflow

## Executive Summary

该仓库已经代码级核验为一个极简的单机单卡预训练研究 harness，而不是多模块、多配置层的通用训练框架。真实训练入口是根目录的 `train.py`，标准启动方式是 `uv run train.py`。真实的一次性准备入口是 `prepare.py`，用于下载数据、训练 tokenizer，并提供训练时复用的 dataloader 与固定评测函数。

配置系统不是 `Hydra`、`YAML` 或独立 `configs/` 目录，而是两层“代码即配置”：

1. `prepare.py` 中的固定常量负责定义不可随实验漂移的运行边界，例如 `MAX_SEQ_LEN`、`TIME_BUDGET`、`EVAL_TOKENS`、缓存目录和数据源。
2. `train.py` 中的模块级常量负责定义本次实验可直接改动的模型与优化超参数，例如 `DEPTH`、`WINDOW_PATTERN`、`TOTAL_BATCH_SIZE`、`MATRIX_LR`。

## Architecture/Flow

```text
┌──────────────┐
│ program.md   │
│ Research SOP │
└──────┬───────┘
       │ guides human/agent edits
       ▼
┌──────────────┐         ┌──────────────────────────────┐
│ prepare.py   │         │ ~/.cache/autoresearch/       │
│ Data Prep    │────────>│ data/ + tokenizer/ artifacts │
└──────┬───────┘         └──────────────┬───────────────┘
       │ exports runtime utilities                     │ loaded by
       ▼                                               ▼
┌─────────────────────────────────────────────────────────────┐
│ train.py                                                    │
│ env setup → tokenizer load → build_model_config → GPT      │
│ → MuonAdamW setup → make_dataloader("train") → train loop  │
│ → evaluate_bpb(..., "val") → summary metrics               │
└─────────────────────────────────────────────────────────────┘
```

## Core Logic

### Verified Entry Points

- 真实训练入口：`train.py`
  - `README.md` 的 quick start 明确使用 `uv run train.py`。
  - `train.py` 没有独立 CLI parser，也没有 `main()` 包装；模块顶层代码在脚本执行时直接完成初始化、训练和评测。
- 真实准备入口：`prepare.py`
  - `prepare.py` 的 `if __name__ == "__main__"` 下使用 `argparse` 暴露 `--num-shards` 和 `--download-workers`，负责一次性数据准备，不负责训练。

### Configuration System

- 固定配置在 `prepare.py`
  - 训练公共边界：`MAX_SEQ_LEN = 2048`、`TIME_BUDGET = 300`、`EVAL_TOKENS = 40 * 524288`
  - 缓存目录：`~/.cache/autoresearch/data`、`~/.cache/autoresearch/tokenizer`
  - 数据源：`karpathy/climbmix-400b-shuffle`
  - 固定验证集：`VAL_SHARD = MAX_SHARD`
- 可实验配置在 `train.py`
  - 模型结构：`ASPECT_RATIO`、`HEAD_DIM`、`WINDOW_PATTERN`、`DEPTH`
  - 优化配置：`TOTAL_BATCH_SIZE`、`EMBEDDING_LR`、`UNEMBEDDING_LR`、`MATRIX_LR`、`SCALAR_LR`、`WEIGHT_DECAY`、`ADAM_BETAS`
  - 设备 batch：`DEVICE_BATCH_SIZE`
- 派生配置
  - `GPTConfig` 是唯一结构化配置对象。
  - `build_model_config(DEPTH)` 根据模块级常量和 `prepare.py` 导入的固定常量在运行时派生最终模型配置。

### Training/Eval Flow

- `train.py` 在顶层完成以下链路：
  1. 设置运行环境变量并探测 `torch.cuda.get_device_capability()`
  2. 依据 GPU capability 选择 `flash-attn3` kernel repo
  3. `Tokenizer.from_directory()` 从缓存目录加载 tokenizer
  4. `build_model_config()` 构建 `GPTConfig`
  5. 初始化 `GPT`、`MuonAdamW`、`make_dataloader(..., "train")`
  6. `torch.compile(model, dynamic=False)` 后进入固定时间预算训练循环
  7. 训练结束后调用 `evaluate_bpb(model, tokenizer, DEVICE_BATCH_SIZE)` 在验证集上评估
- 停止条件不是 epoch 或 step 数，而是 wall-clock `TIME_BUDGET`。因此该仓库的优化目标本质上是“在 5 分钟预算内最优的 `val_bpb`”。

### Core Modules

- `prepare.py`
  - 一次性数据下载
  - BPE tokenizer 训练与缓存
  - `Tokenizer` 封装
  - `make_dataloader`
  - 固定评测函数 `evaluate_bpb`
- `train.py`
  - GPT 模型定义：`GPTConfig`、`CausalSelfAttention`、`MLP`、`Block`、`GPT`
  - 自定义优化器：`MuonAdamW`
  - 学习率、momentum、weight decay schedule
  - 主训练循环与最终 summary 输出
- `program.md`
  - 不是 Python 执行入口，而是 agent/human 的研究控制面与流程约束说明

## Data Sources

- 原始训练/验证数据来自 Hugging Face parquet shards：
  - Base URL: `https://huggingface.co/datasets/karpathy/climbmix-400b-shuffle/resolve/main`
- 训练 tokenizer 时会排除固定验证 shard，只使用训练 shards。
- 评测指标是 `val_bpb`，通过 `evaluate_bpb()` 对固定验证流进行 bits-per-byte 计算，避免 vocab size 改变时的指标失真。

## Code Navigation

| File | Responsibility | Notes |
| --- | --- | --- |
| `train.py` | 真实训练入口、模型、优化器、训练循环 | 顶层执行，无单独 CLI |
| `prepare.py` | 数据下载、tokenizer 训练、dataloader、固定评测 | 通过 CLI 触发一次性准备 |
| `program.md` | 研究流程与 agent 操作准则 | 不参与 Python 执行 |
| `README.md` | 用户级运行说明与设计取舍 | 明确 `uv run prepare.py` / `uv run train.py` |
| `pyproject.toml` | 依赖与 `uv` 源配置 | `torch==2.9.1`，CUDA 128 index |

## Working Guardrails

- 变更训练相关逻辑前，先判断它属于：
  - 固定边界：`prepare.py` 中的数据、tokenizer、评测定义
  - 可实验面：`train.py` 中的模型、优化器和训练策略
- 不要把该仓库误判为“有外部配置系统”的训练框架；当前真实配置面主要就在 Python 常量与 `GPTConfig` 派生链路里。
- 任何性能优化都应优先检查是否改变了固定时间预算、固定验证集或 `evaluate_bpb()` 的可比性。
