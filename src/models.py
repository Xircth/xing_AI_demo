import os, json, torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from src.utils import Config, setup_logger

class ModelFineTuner:
    def __init__(self):
        self.cfg = Config().get('model') # 获取模型配置
        self.model_path = self.cfg['path']
        self.logger = setup_logger('log') # 设置日志器
        self.tokenizer = None
        self.model = None
        
    def load_model(self):
        """加载模型"""
        try:
            self.logger.info(f"加载模型: {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path, 
                torch_dtype=torch.float16,
                device_map="auto"
            )
            self.logger.info("模型加载成功")
            return True
        except Exception as e:
            self.logger.error(f"模型加载失败: {e}")
            return False
        
    def prepare_lora_config(self):
        """准备LoRA配置"""
        return LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )
    
    def _format_example(self, example):
        """格式化训练样本"""
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output = example.get("output", "")
        
        if input_text:
            prompt = f"<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\n{input_text}<|im_end|>\n<|im_start|>assistant\n"
        else:
            prompt = f"<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>assistant\n"
            
        # 在输出内容末尾添加EOS标记，防止模型生成重复内容
        if self.tokenizer and self.tokenizer.eos_token:
            output = output + "<|im_end|>"
        
        # 返回完整的拼接文本
        return {"text": prompt + output}
    
    def prepare_dataset(self, data_path):
        """准备数据集"""
        from datasets import Dataset
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # 格式化数据
            formatted_data = [self._format_example(example) for example in raw_data]
            
            # 创建数据集 - 不进行数据质量过滤
            dataset = Dataset.from_list(formatted_data)
            
            # 对文本进行tokenize处理
            def tokenize_function(examples):
                tokenized = self.tokenizer(examples["text"], truncation=True, 
                                           padding="max_length", max_length=512)
                tokenized["labels"] = tokenized["input_ids"].copy()  # 设置labels与input_ids相同
                return tokenized
            
            # 应用tokenize处理
            tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
            
            # 分割训练集和验证集
            split_dataset = tokenized_dataset.train_test_split(test_size=0.1)
            
            return split_dataset
        except Exception as e:
            self.logger.error(f"准备数据集失败: {e}")
            return None
    
    def train(self, train_data_path, output_dir="models/finetuned", batch_size=4, epochs=3):
        """使用LoRA进行微调"""
        if not self.model:
            if not self.load_model():
                return False
        
        try:
            # 准备数据集
            dataset = self.prepare_dataset(train_data_path)
            if not dataset:
                return False
            
            # 准备LoRA配置
            lora_config = self.prepare_lora_config()
            
            # 应用LoRA
            model = prepare_model_for_kbit_training(self.model)
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
            
            # 准备数据整理器 - 不添加额外过滤条件
            data_collator = DataCollatorForLanguageModeling(tokenizer=self.tokenizer, mlm=False)
            
            # 设置训练参数 - 不使用任何数据过滤或质量检测
            training_args = TrainingArguments(
                output_dir=output_dir,
                learning_rate=3e-4,
                per_device_train_batch_size=batch_size,
                per_device_eval_batch_size=batch_size,
                num_train_epochs=epochs,
                weight_decay=0.01,
                remove_unused_columns=False,  
            )
            
            # 创建训练器
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=dataset["train"],
                eval_dataset=dataset["test"],
                data_collator=data_collator,
            )
            
            # 开始训练
            self.logger.info("开始训练")
            trainer.train()
            
            # 保存模型
            self.logger.info(f"保存模型到 {output_dir}")
            trainer.save_model(output_dir)
            
            return True
        except Exception as e:
            self.logger.error(f"训练失败: {e}")
            return False 