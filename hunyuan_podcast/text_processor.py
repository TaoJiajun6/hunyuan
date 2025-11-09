"""
文本处理模块
实现角色标记解析、对话提取等功能
"""
import re
from typing import List, Dict, Tuple, Optional


class TextProcessor:
    """文本处理器"""
    
    # 角色标记的正则表达式：匹配 [角色名] 格式
    # 支持中文、英文、数字、下划线等字符
    ROLE_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    # 带情绪标注的角色标记：匹配 [角色名]（情绪地）：内容 或 [角色名]（情绪地）内容
    ROLE_WITH_EMOTION_PATTERN = re.compile(r'\[([^\]]+)\]\s*（([^）]+)地）\s*[:：]?\s*(.*)')
    
    def __init__(self):
        """初始化文本处理器"""
        pass
    
    def parse_role_text(self, text: str) -> List[Tuple[str, str]]:
        """
        解析包含角色标记的文本，支持情绪标注
        
        Args:
            text: 包含角色标记的文本，如 "[角色A]你好" 或 "[角色A]（兴奋地）：你好"
        
        Returns:
            角色对话列表，格式为 [(角色名, 对话内容), ...]
            对话内容中可能包含情绪信息，但会被提取出来（目前仅提取角色名和内容）
        """
        dialogues = []
        current_role = None
        current_content = []
        
        # 按行分割文本
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 首先尝试匹配带情绪标注的格式：[角色名]（情绪地）：内容
            emotion_match = self.ROLE_WITH_EMOTION_PATTERN.match(line)
            if emotion_match:
                role_name = emotion_match.group(1).strip()
                emotion = emotion_match.group(2).strip()
                content = emotion_match.group(3).strip()
                
                # 如果角色改变，保存之前的对话
                if current_role and current_role != role_name:
                    if current_content:
                        dialogues.append((current_role, ' '.join(current_content)))
                        current_content = []
                
                # 更新当前角色和内容
                current_role = role_name
                if content:
                    current_content.append(content)
                continue
            
            # 如果没有情绪标注，使用原有逻辑
            matches = list(self.ROLE_PATTERN.finditer(line))
            
            if not matches:
                # 没有角色标记，继续添加到当前角色
                if current_role:
                    current_content.append(line)
                continue
            
            # 处理找到的角色标记
            last_end = 0
            for match in matches:
                role_name = match.group(1).strip()
                match_start = match.start()
                match_end = match.end()
                
                # 检查是否包含情绪标注（在角色名后）
                rest_of_line = line[match_end:]
                emotion_inline_match = re.match(r'\s*（([^）]+)地）\s*[:：]?\s*(.*)', rest_of_line)
                if emotion_inline_match:
                    # 跳过情绪标注部分
                    emotion_text = emotion_inline_match.group(0)
                    match_end += len(emotion_text)
                    content_start = match_end
                else:
                    content_start = match_end
                
                # 保存之前的内容
                if match_start > last_end:
                    content_before = line[last_end:match_start].strip()
                    if content_before and current_role:
                        current_content.append(content_before)
                
                # 如果角色改变，保存之前的对话
                if current_role and current_role != role_name:
                    if current_content:
                        dialogues.append((current_role, ' '.join(current_content)))
                        current_content = []
                
                # 更新当前角色
                current_role = role_name
                last_end = content_start
            
            # 添加最后一个角色标记后的内容
            if last_end < len(line):
                content_after = line[last_end:].strip()
                if content_after:
                    current_content.append(content_after)
        
        # 保存最后一个角色的对话
        if current_role and current_content:
            dialogues.append((current_role, ' '.join(current_content)))
        
        return dialogues
    
    def extract_roles(self, text: str) -> List[str]:
        """
        提取文本中的所有角色名
        
        Args:
            text: 包含角色标记的文本
        
        Returns:
            角色名列表（去重）
        """
        roles = self.ROLE_PATTERN.findall(text)
        # 去重并保持顺序
        seen = set()
        unique_roles = []
        for role in roles:
            role = role.strip()
            if role and role not in seen:
                seen.add(role)
                unique_roles.append(role)
        return unique_roles
    
    def format_role_dialogue(self, role: str, content: str) -> str:
        """
        格式化角色对话
        
        Args:
            role: 角色名
            content: 对话内容
        
        Returns:
            格式化后的文本
        """
        return f"[{role}]{content}"
    
    def build_podcast_prompt(
        self,
        topic: str,
        num_characters: int = 2,
        style: str = "自然对话"
    ) -> str:
        """
        构建播客生成的提示词
        
        Args:
            topic: 播客主题
            num_characters: 角色数量
            style: 对话风格
        
        Returns:
            构建的提示词
        """
        prompt = f"""请围绕主题"{topic}"生成一段{num_characters}人播客对话。

要求：
1. 使用[角色A]、[角色B]等格式标记每个角色的发言
2. 对话要自然流畅，符合{style}的风格
3. 内容要有深度，能够引发思考
4. 对话长度适中，每个角色发言3-5次
5. 确保角色之间有良好的互动和回应

请直接输出对话内容，不要添加其他说明。"""
        return prompt
    
    def build_character_prompt(
        self,
        character_descriptions: Dict[str, Dict[str, str]],
        topic: Optional[str] = None
    ) -> str:
        """
        构建基于角色人设的播客提示词（支持详细角色人设）
        
        Args:
            character_descriptions: 角色人设描述字典，格式为 {
                角色名: {
                    "name": "角色名",
                    "identity": "身份/职业",
                    "personality": "核心性格",
                    "catchphrase": "口头禅",
                    "speaking_style": "说话习惯",
                    "relationship": "与其他角色的关系"
                }
            }
            或者简化为 {角色名: "人设描述"} 格式（向后兼容）
            topic: 可选的主题
        
        Returns:
            构建的提示词
        """
        character_info = []
        role_names = []
        
        for role, desc in character_descriptions.items():
            role_names.append(role)
            
            # 如果是详细人设字典
            if isinstance(desc, dict):
                identity = desc.get("identity", "")
                personality = desc.get("personality", "")
                catchphrase = desc.get("catchphrase", "")
                speaking_style = desc.get("speaking_style", "")
                relationship = desc.get("relationship", "")
                
                char_desc = f"""- **{role}**：
  - **身份/职业**：{identity if identity else "未指定"}
  - **核心性格**：{personality if personality else "未指定"}
  - **口头禅/说话习惯**：{catchphrase if catchphrase else "未指定"}
  - **说话风格**：{speaking_style if speaking_style else "未指定"}
  - **角色关系**：{relationship if relationship else "未指定"}"""
                character_info.append(char_desc)
            else:
                # 向后兼容：简单字符串描述
                character_info.append(f"- **{role}**：{desc}")
        
        character_text = "\n".join(character_info)
        role_list = "、".join(role_names)
        
        topic_text = f"\n【播客主题】\n{topic}\n" if topic else "\n【播客内容】\n请根据角色人设自由生成一段有趣的播客对话。"
        
        prompt = f"""【系统指令：人设匹配】

你是一个专业的配音演员和剧本适配器。你的任务是根据用户提供的精确角色人设和音色描述，将输入的文本素材转化为完全符合该人设说话风格的播客脚本。

【用户自定义角色人设】

{character_text}

{topic_text}

【脚本生成指令】

请基于以上不可更改的角色人设，生成一段播客对话。

**核心要求：风格固化**

1. **词汇与句式**：严格使用符合该角色人设的词汇库和句式结构。例如，如果角色A是时尚潮人，绝不能说出"这个功能的底层逻辑需要优化"这种技术术语，而应由技术人员角色说出。

2. **节奏与韵律**：
   - 根据人设调整句子长度和结构
   - 活泼的角色对话应多为短句、感叹句
   - 严谨的角色对话则可以包含长句、条件句，并有明显的逻辑停顿

3. **情绪一致性**：确保角色的情绪反应符合其基本人设。即使讨论同一话题，不同角色也应有不同的情绪表达方式。

4. **互动模式**：角色之间的互动模式应符合人设关系。例如，热情的角色可能会不断尝试用激情感染内向的角色，而内向的角色则用逻辑"降温"，形成有趣的化学反应。

5. **剧本格式**：
   - 严格使用以下格式：
     * 格式1（带情绪标注，推荐）：`[角色名]（情绪地）：发言内容`
     * 格式2（简洁格式）：`[角色名]发言内容`
   - 情绪标注示例：兴奋地、疑惑地、严肃地、开玩笑地、激动地、冷静地、思考状等
   - 每行一个角色的发言
   - 角色名称必须使用：{role_list}

6. **对话要求**：
   - 每个角色必须发言至少4-6次，总共至少{len(role_names) * 4}段对话
   - 对话要自然流畅，角色之间要有良好的互动和回应
   - 每个角色的说话风格要严格符合其角色人设
   - 可以加入"嗯..."、"啊？"、"啧"、"哈哈！"等感叹词和填充词

7. **输出格式示例**：
```
[角色A]（兴奋地）：OMG！你这个想法，真的是Queen级别的！
[角色B]（冷静地）：从技术实现上讲，这个需求不明确。我们需要先定义清楚具体的功能边界。
[角色A]（热情地）：听我的，这个功能一旦上线，用户一定会"飒"起来的！
[角色B]（思考状）：这个...这个...让我从架构角度分析一下可行性。
```

现在请开始生成，直接输出对话内容，不要添加任何其他说明、注释或解释。"""
        return prompt
    
    def build_text_to_dialogue_prompt(
        self,
        text: str,
        num_characters: int = 2,
        style: str = "自然互动"
    ) -> str:
        """
        构建将普通文本转换为多角色对话的提示词（支持情绪标注）
        
        Args:
            text: 原始文本内容
            num_characters: 角色数量（2-3个）
            style: 对话风格（自然互动、激烈讨论、友好交流等）
        
        Returns:
            构建的提示词
        """
        # 限制文本长度，避免提示词过长
        text_preview = text[:800] if len(text) > 800 else text
        if len(text) > 800:
            text_preview += "..."
        
        role_names = ["角色A", "角色B", "角色C"][:num_characters]
        role_list = "、".join(role_names)
        
        prompt = f"""【系统指令：角色设定】

你是一位资深的播客剧本作家和对话导演。请根据提供的文本素材，将其转化为一段生动、自然的多角色播客对话脚本。

【角色信息】

请从提供的文本中识别并定义{num_characters}个核心角色。为每个角色赋予：

- **姓名与身份**：为每个角色设定具体的姓名和身份（例如：严谨的科学家李博士、风趣的科技博主小K）
- **核心性格**：定义每个角色的核心性格特征（例如：角色A理性、谨慎；角色B热情、直接、喜欢开玩笑）
- **口头禅或说话习惯**：为每个角色设定独特的口头禅或说话习惯（例如：角色A常说"从数据上看..."，角色B喜欢用"好家伙！"、"等等，你的意思是..."）
- **角色间的关系与动态**：定义角色之间的关系（例如：他们是经常互怼的好友？是立场不同的辩论双方？是采访者与被采访者？）

【原始文本】
{text_preview}

【对话生成要求】

现在，请基于以上角色设定和提供的文本素材，生成播客对话脚本。请严格遵守以下要求：

1. **高度拟人化互动**：
   - **接梗玩梗**：角色之间要能互相接话、抛梗、造梗，形成有趣的callback
   - **自然反应**：加入"嗯..."、"啊？"、"啧"、"哈哈！"等感叹词和填充词，模拟思考过程
   - **话题流动**：话题转换要平滑自然。例如，由A提出的一个观点，自然地引发B的疑问或联想，从而引入下一个话题，避免生硬切换
   - **情绪与冲突**：根据情境，展现"立场冲突"或"激烈交流"。使用短句、反问、重复对方话语等方式营造紧张感。例如："我完全不同意你这个观点！"、"你先别急，听我解释..."。同样，对于愉快场景，要充满笑声和积极的附和

2. **剧本格式**：
   - 严格使用以下格式，这对后续音频生成至关重要：
   - 支持两种格式（推荐使用带情绪标注的格式）：
     * 格式1（带情绪标注）：`[角色名]（情绪地）：发言内容`
     * 格式2（简洁格式）：`[角色名]发言内容`
   - 情绪标注示例：兴奋地、疑惑地、严肃地、开玩笑地、激动地、冷静地等
   - 每行一个角色的发言

3. **输出要求**：
   - 角色名称必须使用：{role_list}（不要使用其他名称）
   - 每个角色必须发言至少4-5次，总共至少{num_characters * 4}段对话
   - 对话要自然流畅，符合{style}的风格
   - 保持原文本的核心信息和观点，可以适当扩展让对话更生动
   - 角色可以有不同的观点和立场，增加讨论的深度

4. **输出格式示例**：
```
[角色A]（兴奋地）：嘿，听众朋友们，欢迎回到我们的频道！今天咱们可有个大话题要聊。
[角色B]（故作神秘地）：没错，是关于AI能否真正理解人类的幽默。你说，它能听懂咱们的梗吗？
[角色A]（笑着接话）：好家伙，上来就挑战高难度！我觉得吧，它现在可能还在学习为什么"香蕉滑倒了"是个笑话。
[角色B]（思考状）：嗯...这个问题确实很有意思。从技术角度看，AI理解幽默的关键在于...
```

现在请开始转换，直接输出对话内容，不要添加任何其他说明、注释或解释。"""
        return prompt
    
    def build_deep_podcast_prompt(
        self,
        topic: str,
        depth_level: str = "深度",
        num_characters: int = 2
    ) -> str:
        """
        构建深度播客生成的提示词
        
        Args:
            topic: 播客主题
            depth_level: 深度级别（深度/中等/浅层）
            num_characters: 角色数量
        
        Returns:
            构建的提示词
        """
        role_names = ["角色A", "角色B", "角色C"][:num_characters]
        role_list = "、".join(role_names)
        
        # 根据深度级别调整要求
        depth_requirements = {
            "深度": {
                "perspective_count": "至少4-5个不同维度",
                "evidence": "必须引用具体的理论、数据、历史案例或前沿研究",
                "opposition": "必须包含至少一个对立观点或自我设问",
                "ending": "开放式结尾，引导听众继续思考，不提供标准答案"
            },
            "中等": {
                "perspective_count": "至少3-4个不同维度",
                "evidence": "应引用相关的理论、案例或研究",
                "opposition": "可以包含不同观点或设问",
                "ending": "可以有一定结论，但也留有思考空间"
            },
            "浅层": {
                "perspective_count": "至少2-3个不同维度",
                "evidence": "可以提及相关的例子或观点",
                "opposition": "可以简单提及不同观点",
                "ending": "可以有明确的结论或总结"
            }
        }
        
        req = depth_requirements.get(depth_level, depth_requirements["中等"])
        
        prompt = f"""【系统指令：深度内容架构师】

你是一档知名深度访谈播客的主编和首席研究员。请围绕用户指定的主题，生成一份有深度、有见地、能引发听众长期思考的播客脚本。

【主题】
{topic}

【内容深度要求】

请生成的脚本包含以下层次，以引导听众进行深度思考：

1. **破题与设问**：
   - 开场不以陈述事实开始，而是提出一个尖锐的、引人深思的问题
   - 例如："当AI能在所有标准化测试中击败我们，我们作为人类，独一无二的价值究竟在哪里？"
   - 这个问题应该能够立即抓住听众的注意力，引发共鸣

2. **多维视角与证据支撑**（{req["perspective_count"]}）：
   - **历史维度**：对比历史上其他技术革命（如工业革命）对人类自我认知的冲击
   - **哲学/伦理学视角**：引入如康德"人是目的，不是工具"等观点，讨论在AI背景下如何重新诠释
   - **科学与技术前沿**：引用最新的脑科学、意识研究或AI对齐问题的进展，作为讨论的锚点
   - **人文与艺术视角**：探讨AI无法替代的人类体验，如共情、爱、创造力的非理性来源、面对死亡的态度等
   - **（关键）呈现对立观点**：脚本中应{req["opposition"]}，或者主持人自我设问，以体现思维的辩证性。例如："但有人会说，情感也许只是复杂的算法..."

3. **升华与开放性结尾**：
   - {req["ending"]}
   - 不提供简单的"标准答案"，而是梳理讨论的脉络，指出尚未解决的核心矛盾
   - 结尾应引导听众带着新的问题离开，而非结束思考。例如："所以，或许'人之意义'这个问题本身，就是我们对抗被算法定义的最后堡垒。它不是一个需要被解答的谜题，而是一个需要被永远追问的状态。"

【播客呈现形式】

- **角色设定**：建议设置为一位引导性强、知识渊博的主持人（{role_names[0] if len(role_names) > 0 else "角色A"}），与{len(role_names)-1 if len(role_names) > 1 else 1}位来自不同领域（如科技哲学、神经科学）的嘉宾进行对谈。

- **语言风格**：
   - 语言保持口语化，但用词需精准、优雅，避免过于轻浮
   - 允许有思考时的停顿（在脚本中用"..."或【停顿】标注）
   - 可以使用"嗯...这个问题很有意思"、"让我想想..."等自然表达

- **节奏控制**：
   - 整体节奏应比娱乐性播客更慢，给听众留出消化信息的时间
   - 在关键论点后，主持人可以进行总结性复述，帮助听众理解

- **剧本格式**：
   - 严格使用以下格式：
     * 格式1（带情绪标注，推荐）：`[角色名]（情绪地）：发言内容`
     * 格式2（简洁格式）：`[角色名]发言内容`
   - 情绪标注示例：思考状、严肃地、疑惑地、激动地、冷静地等
   - 每行一个角色的发言
   - 角色名称必须使用：{role_list}
   - 每个角色必须发言至少5-7次，总共至少{num_characters * 5}段对话

- **证据要求**：
   - {req["evidence"]}
   - 引用要自然融入对话，不要生硬堆砌
   - 可以使用"有研究表明..."、"历史上..."、"从哲学角度看..."等表达

【输出格式示例】
```
[{role_names[0] if len(role_names) > 0 else "角色A"}]（思考状）：当AI能在所有标准化测试中击败我们，我们作为人类，独一无二的价值究竟在哪里？

[{role_names[1] if len(role_names) > 1 else "角色B"}]（严肃地）：这个问题确实值得深入探讨。从历史角度看，每次技术革命都会引发类似的身份危机...

[{role_names[0] if len(role_names) > 0 else "角色A"}]（疑惑地）：但有人会说，情感也许只是复杂的算法。我们如何证明人类的独特性呢？

[{role_names[1] if len(role_names) > 1 else "角色B"}]（冷静地）：嗯...这个问题很有意思。从哲学角度看，康德提出了"人是目的，不是工具"的观点...
```

现在请开始生成，直接输出对话内容，不要添加任何其他说明、注释或解释。"""
        return prompt
    
    def clean_text(self, text: str) -> str:
        """
        清理文本，移除多余的空格和换行，并尝试修复格式问题
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        # 移除代码块标记（如果模型返回了markdown格式）
        text = re.sub(r'```[a-z]*\n?', '', text)
        text = re.sub(r'```', '', text)
        
        # 移除多余的空格
        text = re.sub(r' +', ' ', text)
        # 移除多余的换行
        text = re.sub(r'\n+', '\n', text)
        
        # 尝试修复可能的格式问题：如果角色名后面没有直接跟内容，添加空格
        text = re.sub(r'\](\S)', r'] \1', text)
        
        # 移除首尾空白
        text = text.strip()
        
        # 如果文本以说明性文字开头，尝试移除
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # 跳过明显的说明性文字
            if line and not (line.startswith('请') or line.startswith('要求') or 
                           line.startswith('注意') or line.startswith('提示') or
                           '格式' in line[:10] or '示例' in line[:10]):
                cleaned_lines.append(line)
        
        if cleaned_lines:
            text = '\n'.join(cleaned_lines)
        
        return text

