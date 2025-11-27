from datasets import Dataset
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForSeq2Seq, TrainingArguments, Trainer
from peft import LoraConfig, TaskType, get_peft_model
import torch

# -------------------------- 1. 数据加载 --------------------------
train_file = '/root/NLP/datasets/train.jsonl'
val_file = '/root/NLP/datasets/val.jsonl'

# 加载并过滤缺失值
train_df = pd.read_json(train_file, lines=True).dropna(subset=['instruction', 'output']).reset_index(drop=True)
val_df = pd.read_json(val_file, lines=True).dropna(subset=['instruction', 'output']).reset_index(drop=True)

train_ds = Dataset.from_pandas(train_df)
val_ds = Dataset.from_pandas(val_df)

# -------------------------- 2. 加载tokenizer --------------------------
tokenizer = AutoTokenizer.from_pretrained(
    '/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct', 
    use_fast=False, 
    trust_remote_code=True
)
tokenizer.pad_token = tokenizer.eos_token  # 保持pad_token设置

# -------------------------- 3. 数据格式化 --------------------------
def process_func(example):
    MAX_LENGTH = 384  # 教程中统一设置为384
    # 拼接instruction和input（兼容空input）
    user_content = example.get('instruction', '') + example.get('input', '')
    # 按照Qwen2官方Prompt Template格式构建
    instruction = tokenizer(
        f"<|im_start|>system\n你是智慧校园助手，帮助用户处理教务相关问题。<|im_end|>\n"
        f"<|im_start|>user\n{user_content}<|im_end|>\n"
        f"<|im_start|>assistant\n",
        add_special_tokens=False
    )
    # 响应部分不额外添加<|im_end|>，由tokenizer自然处理
    response = tokenizer(f"{example['output']}", add_special_tokens=False)
    
    # 按照教程规范补充pad_token_id和attention_mask
    input_ids = instruction["input_ids"] + response["input_ids"] + [tokenizer.pad_token_id]
    attention_mask = instruction["attention_mask"] + response["attention_mask"] + [1]  # 关注pad token
    labels = [-100] * len(instruction["input_ids"]) + response["input_ids"] + [tokenizer.pad_token_id]  # 对齐教程格式
    
    # 截断处理
    if len(input_ids) > MAX_LENGTH:
        input_ids = input_ids[:MAX_LENGTH]
        attention_mask = attention_mask[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]
    
    return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}

train_tokenized = train_ds.map(process_func, remove_columns=train_ds.column_names)
val_tokenized = val_ds.map(process_func, remove_columns=val_ds.column_names)

# -------------------------- 4. 加载模型 --------------------------
model = AutoModelForCausalLM.from_pretrained(
    '/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct',
    device_map="auto",
    torch_dtype=torch.bfloat16,  # 教程中使用半精度加载（新显卡推荐bfloat16）
    trust_remote_code=True
)
model.enable_input_require_grads()
# 梯度检查点配置（与教程一致）
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

# -------------------------- 5. 配置Lora --------------------------
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    inference_mode=False,
    r=8,
    lora_alpha=32,
    lora_dropout=0.1
)
model = get_peft_model(model, lora_config)

# -------------------------- 6. 配置训练参数 --------------------------
args = TrainingArguments(
    output_dir="./output/Qwen2.5_smart_campus",
    per_device_train_batch_size=4,  # 教程中设置为4
    gradient_accumulation_steps=4,  # 教程中设置为4
    logging_steps=10,
    num_train_epochs=3,
    save_steps=100,
    learning_rate=1e-4,  # 教程中学习率为1e-4
    save_on_each_node=True,
    gradient_checkpointing=True
)

# -------------------------- 7. 启动训练 --------------------------
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_tokenized,
    eval_dataset=val_tokenized,
    data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True)
)

trainer.train()

