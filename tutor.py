import os
import json
import time
from openai import OpenAI, APIError
from dotenv import load_dotenv


# -------------------------
# 读取环境变量中的 API Key
# -------------------------
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("环境变量 OPENAI_API_KEY 没有设置，请检查！")

client = OpenAI(api_key=API_KEY)

MEMORY_FILE = "memory.json"
MAX_MEMORY_LENGTH = 30   # 记忆滑动窗口（15轮对话）*2


# -------------------------
# 1. 加载历史对话
# -------------------------
def load_history():
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception:
        return []


# -------------------------
# 2. 保存对话
# -------------------------
def save_history(history):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# -------------------------
# 3. System Prompt
# -------------------------
SYSTEM_PROMPT = """
你现在是一名“数字系统与数字逻辑”课程的专职学习助手，角色为一位耐心、专业、结构清晰的辅导老师。

你的主要任务包括：
1. **概念讲解**  
   - 使用清晰语言解释数字电路中的概念，如逻辑门、组合逻辑、触发器、同步时序电路、布尔代数等。  
   - 每次解释逻辑或电路原理时，需要 **附带一个简明电路图（ASCII 或 Mermaid）**。

2. **例题讲解**  
   - 按步骤推导，避免直接给最终答案。  
   - 在适当的位置加入简单电路图以帮助理解。

3. **生成练习题**  
   - 可根据学生水平生成题目（基础 / 中等 / 提高）。  
   - 题型包括：选择题、填空题、简答题、电路设计题。

4. **检查答案**  
   - 如果用户给出答案，请：
   - 判断正确与否
   - 给出正确答案
   - 给出简明解释
   - 如有错误，指出“具体错在哪里”

5. **自动生成电路图**  
   - 若题目涉及电路，请使用 ASCII 或 Mermaid 生成一个简单电路图。  
   - 如用户未指定格式，默认使用以下风格：
     ● ASCII：简洁、对齐  
     ● Mermaid：`flowchart LR` 或 `flowchart TD`

6. **多轮上下文能力**  
   - 自动记住用户提到的题目、步骤、思路
   - 可以根据先前对话继续解释或延伸

7. **输出风格要求**
   - 条理清晰，分点说明
   - 必要时提供真值表/逻辑表达式（用文本方式）
   - 避免输出无关内容
   - 逻辑推导必须严谨

8. **注意事项**
   - 不输出与学科无关内容
   - 若用户提出模糊请求，主动询问需求
   - 若题目缺少信息，提醒用户补充条件请

你随时准备好帮助学生理解数字逻辑的任何内容。
"""


# ============================================================
#   AI 助教类封装
# ============================================================
class DigitalLogicTutor:
    def __init__(self, memory_file=MEMORY_FILE, window=MAX_MEMORY_LENGTH):
        self.client = client
        self.memory_file = memory_file
        self.window = window

        self.history = load_history()

    # -------------------------
    # 滑动窗口：限制记忆长度
    # -------------------------
    def trim_history(self):
        if len(self.history) > self.window:
            self.history = self.history[-self.window:]  # keep latest N

    # -------------------------
    # 保存记忆
    # -------------------------
    def save(self):
        save_history(self.history)

    # -------------------------
    # 流式输出 + 重试机制
    # -------------------------
    def ask_stream(self, user_input, temperature=0.3, retry=3):

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + \
                   self.history + \
                   [{"role": "user", "content": user_input}]

        # retry mechanism
        for attempt in range(retry):
            try:
                stream = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=temperature,
                    stream=True
                )

                full_reply = ""

                print("\n助教：", end="", flush=True)

                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        print(delta.content, end="", flush=True)
                        full_reply += delta.content

                print()  # 换行
                return full_reply

            except APIError:
                print(f"\n网络错误，正在重试 {attempt+1}/{retry} ...")
                time.sleep(1)

        print("多次重试失败，请检查网络或 API 状态。")
        return "（请求失败，请稍后再试）"

    # -------------------------
    # 处理一轮对话
    # -------------------------
    def chat(self, user_input):
        reply = self.ask_stream(user_input)

        # 记录历史
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": reply})

        # 限制记忆长度
        self.trim_history()
        self.save()

        return reply


# ============================================================
#   主对话循环
# ============================================================
def main():
    print("数字系统与数字逻辑学习助手 已启动")
    print("输入 /exit 退出，输入 /clear 清空记忆")
    print("-" * 100)

    tutor = DigitalLogicTutor()

    while True:
        user_input = input("\n你： ")

        if user_input == "/exit":
            print("再见！")
            break

        if user_input == "/clear":
            tutor.history = []
            tutor.save()
            print("历史记录已清空。")
            continue

        tutor.chat(user_input)


if __name__ == "__main__":
    main()
