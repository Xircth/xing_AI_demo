#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""大模型微调脚本"""

import os,sys,argparse,torch
# Add parent directory to sys.path to find src module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.models import ModelFineTuner
from src.utils import setup_logger,Config
from transformers import EarlyStoppingCallback,AutoModelForCausalLM,AutoTokenizer,TrainingArguments,DataCollatorForLanguageModeling
from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
from trl import SFTTrainer
from datasets import Dataset,load_dataset

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="大模型LoRA微调脚本")
    # Adjust default data path relative to the parent directory
    parser.add_argument("--data",type=str,default="../resume_dataset.json",help="训练数据JSON文件路径")
    parser.add_argument("--output",type=str,default="models/finetuned",help="模型输出目录")
    parser.add_argument("--batch_size",type=int,default=1,help="训练批次大小")
    parser.add_argument("--epochs",type=int,default=5,help="训练轮数")
    parser.add_argument("--learning_rate",type=float,default=4e-5,help="学习率")
    parser.add_argument("--lora_r",type=int,default=16,help="LoRA秩")
    parser.add_argument("--lora_alpha",type=int,default=32,help="LoRA缩放因子")
    parser.add_argument("--patience",type=int,default=2,help="早停耐心值")
    parser.add_argument("--max_length",type=int,default=512,help="最大序列长度")
    parser.add_argument("--warmup_steps",type=int,default=5,help="预热步数")
    parser.add_argument("--eval_steps",type=int,default=20,help="评估步数")
    parser.add_argument("--save_steps",type=int,default=20,help="保存步数")
    parser.add_argument("--tag",type=str,default="resume_assistant",help="模型标签")
    return parser.parse_args()

def main():
    """主函数"""
    # 解析参数
    args = parse_args()
    
    # 设置日志
    logger = setup_logger('log')
    logger.info("开始微调模型")
    
    # 获取配置
    cfg = Config() # Assuming Config loads relative to config file or uses absolute paths
    model_path = cfg.get('model')['path']
    
    # 检查数据文件 (using args.data which now defaults to ../resume_dataset.json)
    if not os.path.exists(args.data):
        logger.error(f"训练数据文件不存在: {args.data}")
        sys.exit(1)
    
    # 确保输出目录存在 (adjust path relative to parent dir)
    output_dir = os.path.join("..", f"models/{args.tag}/checkpoints")
    os.makedirs(output_dir,exist_ok=True)
    
    try:
        # 加载模型和分词器
        logger.info(f"加载基础模型: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        # 设置填充token
        tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # 准备数据集
        logger.info(f"加载数据集: {args.data}")
        with open(args.data,'r',encoding='utf-8') as f:
            import json
            raw_data = json.load(f)
        
        # 准备指令格式数据
        def format_example(example):
            instruction = example.get("instruction","")
            input_text = example.get("input","")
            output = example.get("output","")
            
            if input_text:
                prompt = f"<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\n{input_text}<|im_end|>\n<|im_start|>assistant\n"
            else:
                prompt = f"<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>assistant\n"
                
            # 在输出内容末尾添加EOS标记
            if tokenizer.eos_token:
                output = output + "<|im_end|>"
            
            # 返回text和对应标签
            return {
                "text": prompt + output
            }
        
        formatted_data = [format_example(example) for example in raw_data]
        dataset = Dataset.from_list(formatted_data)
        
        # 分割训练集和验证集
        split_dataset = dataset.train_test_split(test_size=0.1)
        train_dataset = split_dataset["train"]
        eval_dataset = split_dataset["test"]
        
        # 设置早停回调
        early_stopping_callback = EarlyStoppingCallback(
            early_stopping_patience=args.patience,
            early_stopping_threshold=0.01,
        )
        
        # 配置LoRA
        logger.info("配置LoRA参数")
        # 为AMD显卡适配，移除CUDA特定设置
        model = prepare_model_for_kbit_training(model)
        
        # 创建LoRA配置对象
        lora_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            lora_dropout=0,
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        # 使用lora_config对象创建peft模型
        model = get_peft_model(model, peft_config=lora_config)
        model.print_trainable_parameters()
        
        # 设置训练参数
        logger.info(f"开始训练: 批次={args.batch_size}, 轮数={args.epochs}, 学习率={args.learning_rate}")
        
        # 设置训练参数
        training_args = TrainingArguments(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=1,
            warmup_steps=args.warmup_steps,
            num_train_epochs=args.epochs,
            learning_rate=args.learning_rate,
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            output_dir=output_dir,
            report_to="none",
            evaluation_strategy="steps",
            eval_steps=args.eval_steps,
            save_strategy="steps",
            save_steps=args.save_steps,
            save_total_limit=5,
            metric_for_best_model="eval_loss",
            load_best_model_at_end=True,
            # 设置最大序列长度
            max_seq_length=args.max_length
        )
        
        # 使用SFTTrainer进行训练，使用最简参数避免兼容性问题
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            args=training_args,
            callbacks=[early_stopping_callback],
        )
        
        # 开始训练
        trainer_stats = trainer.train()
        
        # 保存最终模型
        # Adjust final save path relative to parent dir
        final_model_output_dir = os.path.join("..", args.output)
        logger.info(f"训练完成，保存模型到: {final_model_output_dir}")
        trainer.save_model(final_model_output_dir)
        
        logger.info("微调成功完成")
        return True
    except Exception as e:
        logger.error(f"训练过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    main() 