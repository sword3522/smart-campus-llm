"""
模型服务封装 - 统一管理 LoRA 微调模型的加载和推理
"""
from __future__ import annotations

import torch
from typing import Optional, List, Dict, Literal
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


class ModelService:
    """
    智慧校园助手模型服务
    封装 Qwen2.5-7B-Instruct + LoRA 的加载和推理
    """
    
    _instance: Optional["ModelService"] = None
    
    def __init__(
        self,
        base_model_path: str = "/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct/",
        lora_path: str = "/root/NLP/lora/output/Qwen2.5_smart_campus/checkpoint-237",
        device_map: str = "auto",
        torch_dtype: torch.dtype = torch.bfloat16,
    ):
        self.base_model_path = base_model_path
        self.lora_path = lora_path
        self.device_map = device_map
        self.torch_dtype = torch_dtype
        
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[PeftModel] = None
        self._loaded = False
    
    @classmethod
    def get_instance(cls, **kwargs) -> "ModelService":
        """单例模式，避免重复加载模型"""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def load(self) -> None:
        """加载模型和分词器"""
        if self._loaded:
            print("模型已加载，跳过重复加载")
            return
        
        print(f"正在加载分词器: {self.base_model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_path,
            use_fast=False,
            trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        print(f"正在加载基座模型: {self.base_model_path}")
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            device_map=self.device_map,
            torch_dtype=self.torch_dtype,
            trust_remote_code=True
        )
        
        print(f"正在加载 LoRA 权重: {self.lora_path}")
        self.model = PeftModel.from_pretrained(base_model, self.lora_path)
        self.model.eval()
        
        self._loaded = True
        print("✓ 模型加载完成")
    
    def generate(
        self,
        instruction: str,
        input_text: str,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        生成回复
        
        Args:
            instruction: 系统指令（角色设定）
            input_text: 用户输入内容
            max_new_tokens: 最大生成长度
            temperature: 温度参数
            top_p: 采样策略
        
        Returns:
            模型生成的回复文本
        """
        if not self._loaded:
            self.load()
        
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_text}
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                model_inputs.input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # 截取新生成的部分
        generated_ids = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return response.strip()
    
    def summarize_news(
        self,
        news_content: str,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> str:
        """
        生成新闻总结（差异化总结）
        
        Args:
            news_content: 新闻内容（可包含多条新闻）
            user_identity: 用户身份 (student/teacher)
        
        Returns:
            针对特定身份的新闻总结
        """
        identity_cn = "学生" if user_identity == "student" else "教师"
        instruction = f"你是一个智慧校园助手。当前用户是【{identity_cn}】，请总结以下教务通知。"
        
        return self.generate(instruction, news_content)
    
    def answer_question(
        self,
        history_briefs: str,
        user_question: str,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> str:
        """
        基于历史简报回答用户问题
        
        Args:
            history_briefs: 历史新闻简报（格式: [日期]：简报内容）
            user_question: 用户的问题
            user_identity: 用户身份 (student/teacher)
        
        Returns:
            基于历史简报的回答
        """
        identity_cn = "学生" if user_identity == "student" else "教师"
        instruction = (
            f"你是智慧校园助手，帮助用户处理教务相关问题。"
            f"你是一个智慧校园助手。当前用户是【{identity_cn}】。"
            f"请根据给定的【过去一段时间的新闻简报】，回答用户的问题。"
            f"如果简报中没有相关信息，请直接说：最近没有该类新闻/通知，不知道。"
        )
        
        input_text = f"{history_briefs}\n\n【用户问题】：{user_question}"
        
        return self.generate(instruction, input_text)
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._loaded


# 便捷函数
def get_model_service(**kwargs) -> ModelService:
    """获取模型服务单例"""
    return ModelService.get_instance(**kwargs)

