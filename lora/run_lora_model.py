from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from peft import PeftModel

model_path = '/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct/'  # 基座模型路径
lora_path = '/root/NLP/lora/output/Qwen2.5_smart_campus/checkpoint-237'  # LoRA权重路径


tokenizer = AutoTokenizer.from_pretrained(
    model_path, 
    use_fast=False, 
    trust_remote_code=True
)
tokenizer.pad_token = tokenizer.eos_token 


base_model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",  
    torch_dtype=torch.bfloat16,  
    trust_remote_code=True
)


model = PeftModel.from_pretrained(base_model, lora_path)
model.eval()  


history_brief = """【历史简报】：
[2023-04-28]：【截止日期】：项目申报截止时间为2023年5月6日22:00；立项项目需在5月18日前完成筹备。
【学分/综测】：暂无明确提及学分或综合素质测评加分，但参与立项项目可能有助于实践经历认定，建议咨询所在学院确认。
【报名入口/操作步骤】：1. 填写《“西安交通大学校园开放日专题路演”项目申报表》；2. 于5月6日22:00前将报名表发送至邮箱dean@xjtu.edu.cn；3. 提交后需填写指定链接（文中未提供具体链接）。
【注意事项】：申报团队须为师生科研团队或学生社团，且需依托学院、书院或职能部门；项目应具备强互动性、可参与性和吸引力；科研类项目经费支持原则上不超过8000元，文化类不超过4000元；活动定于5月21日全天举行，需提前做好筹备与展示准备。
[2023-05-04]：【报名数学建模竞赛】：请关注2023年西安交通大学大学生数学建模竞赛通知，该竞赛为全国性重要赛事，有助于提升实践创新能力，相关信息详见实践教学中心链接 http://pec.xjtu.edu.cn/info/1191/3591.htm，请及时查看并按要求报名准备。【领取获奖证书】：获得第十四届全国大学生数学竞赛奖项的同学，请于2023年5月5日至6日每日15:00-19:00，前往数学楼101室领取证书，建议提前核对附件中的获奖名单，避免遗漏。"""

user_question = "最近有没有什么竞赛或者项目能参加的？"


messages = [
    {
        "role": "system", 
        "content": "你是智慧校园助手，帮助用户处理教务相关问题。你是一个智慧校园助手。当前用户是【学生】。请根据给定的【过去一段时间的新闻简报】，回答用户的问题。如果简报中没有相关信息，请直接说：最近没有该类新闻/通知，不知道。"
    },
    {
        "role": "user", 
        "content": f"{history_brief}\n\n【用户问题】：{user_question}"
    }
]


text = tokenizer.apply_chat_template(
    messages, 
    tokenize=False, 
    add_generation_prompt=True  
)

model_inputs = tokenizer([text], return_tensors="pt").to('cuda')


with torch.no_grad():  
    generated_ids = model.generate(
        model_inputs.input_ids,
        max_new_tokens=1024,  # 最大生成长度
        temperature=0.7,     # 随机性
        top_p=0.9,           # 采样策略
        do_sample=True,      # 采样生成
        eos_token_id=tokenizer.eos_token_id
    )


generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]


print("【智慧校园助手回复】：")
print(response)