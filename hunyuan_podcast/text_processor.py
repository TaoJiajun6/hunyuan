"""
文本处理模块
实现角色标记解析、对话提取等功能
"""
import re
import json
from typing import List, Dict, Tuple, Optional, Any


class TextProcessor:
    """文本处理器"""
    
    # 角色标记的正则表达式：匹配 [角色名] 格式
    # 支持中文、英文、数字、下划线等字符
    ROLE_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    # 带情绪标注的角色标记：匹配 [角色名]（情绪地）：内容 或 [角色名]（情绪地）内容
    # 也匹配动作描述：[角色名]（思考状）：内容 或 [角色名]（点头）：内容
    ROLE_WITH_EMOTION_PATTERN = re.compile(r'\[([^\]]+)\]\s*（([^）]+)地）\s*[:：]?\s*(.*)')
    
    # 带动作描述的角色标记：匹配 [角色名]（思考状）：内容 或 [角色名]（点头）：内容（不包含"地"字）
    ROLE_WITH_ACTION_PATTERN = re.compile(r'\[([^\]]+)\]\s*[（(]([^）)]+?)[）)]\s*[:：]?\s*(.*)')
    
    def __init__(self):
        """初始化文本处理器"""
        pass
    
    def clean_dialogue_content(self, content: str) -> str:
        """
        清理对话内容，移除可能误包含的情绪描述词和动作描述
        
        Args:
            content: 原始对话内容
        
        Returns:
            清理后的对话内容
        """
        if not content:
            return content
        
        # 移除内容中的音效标注
        content = re.sub(r'\[音效[：:][^\]]+\]', '', content).strip()
        
        # 移除括号内的动作描述词（如 (点头)、(思考状)、(Nods)、(Thinking) 等）
        # 支持中文括号（）和英文括号()，使用非贪婪匹配
        content = re.sub(r'[（(][^）)]*?[）)]', '', content)
        
        # 移除内容中可能误包含的情绪描述词（防止模型错误生成）
        # 移除类似"我兴奋地说"、"他疑惑地说"等模式
        content = re.sub(r'[我他她它]+\s*[兴奋疑惑严肃激动冷静思考]+[地]?\s*[说讲道]', '', content).strip()
        
        # 移除单独的情绪词（如果出现在句子开头）
        emotion_words = ['兴奋地', '疑惑地', '严肃地', '激动地', '冷静地', '思考状', '笑着', '故作神秘地', 
                        '热情地', '接话', '点头', '摇头', '打断', '总结性地']
        for word in emotion_words:
            if content.startswith(word):
                content = content[len(word):].strip()
                # 移除可能的标点
                content = re.sub(r'^[，,：:]\s*', '', content)
        
        # 移除开头的"我"、"他"、"她"等代词后跟情绪词的模式
        content = re.sub(r'^[我他她它]\s*[兴奋疑惑严肃激动冷静思考]+[地]?\s*[，,：:]?\s*', '', content)
        
        # 清理可能出现的多余空格
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def parse_role_text(self, text: str) -> List[Tuple[str, str]]:
        """
        解析包含角色标记的文本，支持情绪标注和音效标注
        
        Args:
            text: 包含角色标记的文本，如 "[角色A]你好" 或 "[角色A]（兴奋地）：你好"
        
        Returns:
            角色对话列表，格式为 [(角色名, 对话内容), ...]
            对话内容中可能包含情绪信息和音效标注，但会被提取出来（目前仅提取角色名和内容）
            音效标注（如[音效：xxx]）会被跳过，不包含在对话内容中
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
            
            # 跳过纯音效标注行（如 [音效：xxx]）
            if re.match(r'^\[音效[：:].*\]$', line):
                continue
            
            # 首先尝试匹配带情绪标注的格式：[角色名]（情绪地）：内容
            emotion_match = self.ROLE_WITH_EMOTION_PATTERN.match(line)
            if emotion_match:
                role_name = emotion_match.group(1).strip()
                emotion = emotion_match.group(2).strip()
                content = emotion_match.group(3).strip()
                
                # 清理对话内容，移除可能误包含的情绪描述词和音效标注
                content = self.clean_dialogue_content(content)
                
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
            
            # 尝试匹配带动作描述的格式：[角色名]（思考状）：内容 或 [角色名]（点头）：内容
            action_match = self.ROLE_WITH_ACTION_PATTERN.match(line)
            if action_match:
                role_name = action_match.group(1).strip()
                action = action_match.group(2).strip()
                content = action_match.group(3).strip()
                
                # 清理对话内容，移除可能误包含的动作描述词和音效标注
                content = self.clean_dialogue_content(content)
                
                # 如果角色改变，保存之前的对话
                if current_role and current_role != role_name:
                    if current_content:
                        dialogues.append((current_role, ' '.join(current_content)))
                        current_content = []
                
                # 更新当前角色和内容（动作描述会被跳过，不包含在内容中）
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
                
                # 检查是否包含情绪标注或动作描述（在角色名后）
                rest_of_line = line[match_end:]
                # 匹配情绪标注格式：（情绪地）或动作描述格式：（思考状）、（点头）等
                # 支持中文括号（）和英文括号()
                emotion_inline_match = re.match(r'\s*[（(][^）)]*?[）)]\s*[:：]?\s*(.*)', rest_of_line)
                if emotion_inline_match:
                    # 跳过情绪标注或动作描述部分
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
                    # 清理对话内容
                    content_after = self.clean_dialogue_content(content_after)
                    if content_after:
                        current_content.append(content_after)
        
        # 保存最后一个角色的对话
        if current_role and current_content:
            dialogues.append((current_role, ' '.join(current_content)))
        
        return dialogues
    
    def extract_roles(self, text: str) -> List[str]:
        """
        提取文本中的所有角色名（排除音效和音乐标记）
        
        Args:
            text: 包含角色标记的文本
        
        Returns:
            角色名列表（去重）
        """
        roles = self.ROLE_PATTERN.findall(text)
        # 去重并保持顺序，同时过滤掉音效和音乐标记
        seen = set()
        unique_roles = []
        
        # 需要排除的关键词
        exclude_keywords = ['音效', '音乐', '开场', '结束', '背景']
        
        for role in roles:
            role = role.strip()
            if not role:
                continue

            # 过滤掉明显的二进制或不可打印字符串（例如直接把 docx 二进制解码为字符串的情况）
            # 如果包含不可打印字符或过长，则视为无效角色
            if not role.isprintable():
                continue
            if '\x00' in role:
                continue
            if len(role) > 64:
                # 过长的角色名通常不是有效的角色标识，跳过
                continue

            # 跳过音效和音乐标记
            # 检查是否包含排除关键词
            should_exclude = False
            for keyword in exclude_keywords:
                if keyword in role:
                    should_exclude = True
                    break

            # 检查是否是音效格式：[音效：xxx] 或 [音效:xxx]
            if role.startswith('音效') or '音效' in role:
                should_exclude = True

            # 检查是否是音乐格式：[开场音乐...] 或 [结束音乐...] 或 [音乐...]
            if '音乐' in role:
                should_exclude = True

            if should_exclude:
                continue

            # 只添加真正的角色标记
            if role not in seen:
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

5. **剧本格式**（SoulX-Podcast兼容格式）：
   - **主要格式**：`[角色名]对话内容`（最简洁，SoulX-Podcast原生格式，强烈推荐）
   - **可选格式**：`[角色名]（情绪地）对话内容`（支持情绪标注，但情绪标注是可选的）
   - **重要**：不要使用冒号，直接写对话内容
   - 情绪标注示例：兴奋地、疑惑地、严肃地、开玩笑地、激动地、冷静地、思考状等
   - 每行一个角色的发言，角色之间建议有空行间隔，让对话更清晰
   - 角色名称必须使用：{role_list}
   - **角色间隔**：角色对话之间要有自然的间隔，每个角色发言后要有适当的停顿，让对话节奏更舒缓

6. **对话要求**：
   - 每个角色必须发言至少4-6次，总共至少{len(role_names) * 4}段对话
   - 对话要自然流畅，角色之间要有良好的互动和回应
   - 每个角色的说话风格要严格符合其角色人设
   - 可以加入"嗯..."、"啊？"、"啧"、"哈哈！"等感叹词和填充词

7. **输出格式示例**（SoulX-Podcast兼容格式）：
**示例1：简洁格式（推荐）**
```
[角色A]OMG！你这个想法，真的是Queen级别的！

[角色B]从技术实现上讲，这个需求不明确。我们需要先定义清楚具体的功能边界。

[角色A]听我的，这个功能一旦上线，用户一定会"飒"起来的！

[角色B]这个...这个...让我从架构角度分析一下可行性。
```

**示例2：带情绪标注格式（可选）**
```
[角色A]（兴奋地）OMG！你这个想法，真的是Queen级别的！

[角色B]（冷静地）从技术实现上讲，这个需求不明确。我们需要先定义清楚具体的功能边界。

[角色A]（热情地）听我的，这个功能一旦上线，用户一定会"飒"起来的！

[角色B]（思考状）这个...这个...让我从架构角度分析一下可行性。
```

现在请开始生成，直接输出对话内容，不要添加任何其他说明、注释或解释。"""
        return prompt
    
    def build_text_to_dialogue_prompt(
        self,
        text: str,
        num_characters: int = 2,
        podcast_name: Optional[str] = None,
        topic: Optional[str] = None,
        character_descriptions: Optional[Dict[str, Dict[str, str]]] = None,
        scene_types: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> str:
        """
        构建将普通文本转换为多角色对话的提示词（支持情绪标注和完整播客结构）
        
        Args:
            text: 原始文本内容
            num_characters: 角色数量（2-3个）
            podcast_name: 播客名称（可选）
            topic: 本期主题（可选）
            character_descriptions: 角色设定字典，格式为 {
                角色名: {
                    "name": "角色名",
                    "personality": "性格特点",
                    "speaking_style": "说话风格"
                }
            }
            scene_types: 互动场景类型列表，如 ["接梗玩梗", "立场冲突"] 等
            category: 播客分类（可选），如：商业、科技、财经、新闻、影视、自我成长与自愈、职场万象、学习类、娱乐八卦类、考题、文化艺术、职场类—人际关系、学生类—求职就业等
        
        Returns:
            构建的提示词
        """
        # 限制文本长度，避免提示词过长（增加到2000字符以支持更长的文本）
        text_preview = text[:2000] if len(text) > 2000 else text
        if len(text) > 2000:
            text_preview += "..."
        
        role_names = ["角色A", "角色B", "角色C"][:num_characters]
        role_list = "、".join(role_names)
        
        # 构建播客基本信息部分
        podcast_info = ""
        if podcast_name:
            podcast_info += f"播客名称：{podcast_name}\n"
        if topic:
            podcast_info += f"本期主题：{topic}\n"
        if category:
            podcast_info += f"播客分类：{category}\n"
        
        # 构建角色设定部分
        character_info = ""
        if character_descriptions:
            character_info = "\n2. 角色设定（2-3个角色）\n\n"
            for i, (role, desc) in enumerate(character_descriptions.items(), 1):
                if i > num_characters:
                    break
                name = desc.get("name", role)
                personality = desc.get("personality", "")
                speaking_style = desc.get("speaking_style", "")
                character_info += f"角色{i}名称：{name}\n"
                if personality:
                    character_info += f"性格特点：{personality}\n"
                if speaking_style:
                    character_info += f"说话风格：{speaking_style}\n"
                character_info += "\n"
        else:
            character_info = f"\n请从提供的文本中识别并定义{num_characters}个核心角色。为每个角色赋予：\n"
            character_info += "- **姓名与身份**：为每个角色设定具体的姓名和身份\n"
            character_info += "- **核心性格**：定义每个角色的核心性格特征\n"
            character_info += "- **说话风格**：定义每个角色的说话风格和习惯\n"
        
        # 构建场景类型要求
        scene_requirements = ""
        if scene_types:
            scene_requirements = "\n【特定场景要求】\n\n"
            if "接梗玩梗" in scene_types or "接梗玩梗的轻松交流" in scene_types:
                scene_requirements += "- **接梗玩梗**：至少包含3处明显的玩梗互动，形成callback，角色之间要能互相接话、抛梗、造梗\n"
            if "立场冲突" in scene_types or "立场冲突的激烈辩论" in scene_types:
                scene_requirements += "- **立场冲突**：要有明显的观点对立，使用短句、反问、情绪化表达，营造紧张感\n"
            if "访谈对话" in scene_types or "愉快合作" in scene_types or "愉快合作的访谈对话" in scene_types:
                scene_requirements += "- **访谈场景**：明确区分主持人和嘉宾角色，包含深度提问和回应\n"
            if "不愉快的质疑访谈" in scene_types:
                scene_requirements += "- **质疑访谈**：包含质疑、反驳、解释等互动，保持对话的紧张感\n"
        
        # 构建播客基本信息默认值（避免在f-string表达式中使用反斜杠）
        default_podcast_info = "播客名称：[由文本内容推断]\n本期主题：[由文本内容推断]\n"
        final_podcast_info = podcast_info if podcast_info else default_podcast_info
        
        # 构建场景类型字符串
        scene_types_str = ', '.join(scene_types) if scene_types else "自然互动交流"
        
        # 构建分类相关的指导信息
        category_section = ""
        if category:
            # 根据分类提供具体指导（已合并重复分类）
            category_styles = {
                "商业": "注重商业逻辑、市场分析、商业模式、创业经验、创新思维，使用专业术语但要通俗易懂，对话要有深度和实用性",
                "科技": "注重技术原理、科学原理、科学发现、发展趋势、创新应用，保持专业性和前瞻性，语言清晰准确、易懂",
                "财经": "注重经济分析、投资理财、市场趋势，使用财经术语但要解释清楚，内容要有参考价值",
                "新闻": "注重事实陈述、多角度分析、时效性，保持客观中立，语言简洁明了",
                "影视": "注重剧情分析、角色解读、影视文化，语言生动有趣，可以引用经典台词",
                "音乐": "注重音乐赏析、音乐文化、音乐创作，语言优雅有趣，要有艺术性和感染力",
                "文化艺术": "注重文化内涵、艺术赏析、历史背景、书籍推荐、阅读心得、文学赏析，语言优雅有深度，要有文化底蕴",
                "历史": "注重历史事件、人物故事、历史背景，语言生动有趣，要有故事性和深度",
                "哲学思考": "注重哲学思辨、人生思考、价值探讨，语言深刻优雅，要有深度和启发性",
                "自我成长": "注重心理分析、行为解读、成长故事、情感共鸣、心理应用，语言温暖治愈、专业易懂，要有启发性和正能量",
                "职场": "注重职场经验、人际关系、沟通技巧、人际交往、职场情商、职业发展、求职技巧、职业规划、面试经验，语言实用接地气，要有真实感和代入感、场景感和实用性",
                "学习": "注重知识讲解、学习方法、学习技巧、题目解析、解题思路、知识点梳理，语言清晰易懂、严谨清晰，要有实用性和可操作性、逻辑严密",
                "教育育儿": "注重育儿知识、教育方法、亲子关系，语言温和耐心，要有实用性和可操作性",
                "情感恋爱": "注重情感分析、恋爱技巧、情感故事，语言温暖真诚，要有共鸣感和代入感",
                "健康养生": "注重健康知识、养生方法、疾病预防、运动技巧、健身方法、训练计划，语言温和专业、积极向上，要有科学性和实用性、激励性和可操作性",
                "旅游": "注重旅行体验、目的地介绍、旅行攻略，语言生动有趣，要有画面感和代入感",
                "美食": "注重烹饪技巧、美食文化、餐厅推荐，语言诱人有趣，要有色香味俱全的描述",
                "生活方式": "注重生活技巧、生活态度、生活分享，语言轻松有趣，要有实用性和共鸣感",
                "娱乐": "注重趣味性、轻松幽默、话题性、幽默搞笑、喜剧表演、轻松对话，语言活泼有趣，节奏可以更快，要有趣味性和娱乐性",
                "游戏电竞": "注重游戏攻略、电竞赛事、游戏文化，语言活泼有趣，要有竞技性和趣味性",
                "体育": "注重体育赛事、运动技巧、体育文化，语言激情有力，要有竞争性和观赏性",
                "时尚美妆": "注重时尚趋势、美妆技巧、穿搭建议，语言时尚有趣，要有实用性和美观性",
                "汽车": "注重汽车评测、驾驶技巧、汽车文化，语言专业有趣，要有实用性和专业性",
                "法律": "注重法律知识、案例分析、法律应用，语言严谨准确，要有专业性和实用性",
                "宠物": "注重宠物护理、训练技巧、宠物故事，语言温馨有趣，要有实用性和情感共鸣"
            }
            
            style_guide = category_styles.get(category, "根据分类特点调整对话风格和内容深度")
            
            category_guidance_text = f"""**播客分类：{category}**

请根据"{category}"分类的特点调整生成风格和内容深度：
- {style_guide}
- 对话内容要符合该分类的受众期待和知识水平
- 使用的专业术语要适当，确保听众能够理解
- 整体风格要与分类特点保持一致"""
            
            # 构建分类部分（避免在f-string表达式中使用反斜杠）
            category_section = f"5. 播客分类\n\n{category}\n{category_guidance_text}\n"
        
        # 构建完整的提示词
        prompt = f"""【核心指令】

你是一位专业的播客编剧和对话导演。请根据提供的文本素材，将其转化为一段结构完整、互动自然、符合真人交流方式的多角色播客对话脚本。

**重要：本次播客要求时长达到4-5分钟，请生成足够丰富和深入的对话内容。对话总字数建议1500-2500字（纯对话内容），每个角色至少发言15-20次。**

【用户输入区】

1. 播客基本信息

{final_podcast_info}

{character_info}

3. 文本素材

{text_preview}

4. 互动场景类型

{scene_types_str}
{category_section}

【生成要求 - 固定部分】

1. 播客结构

[角色A]大家好，欢迎收听《{podcast_name if podcast_name else "本期播客"}》！我是[角色A名字]。
[角色B]我是[角色B名字]。今天我们要聊一个很有意思的话题：{topic if topic else "[本期主题]"}。
[角色A]没错！说到这个话题，我最近发现...[自然引入主题]

[讨论主体 - 基于文本素材展开，要充分展开讨论，包含多个角度、深入分析、案例分享、观点碰撞等，确保内容丰富，时长达到4-5分钟]

[角色C]好了，今天关于{topic if topic else "[本期主题]"}的讨论就到这里。
[角色A]感谢大家的收听！如果有什么想法，欢迎在评论区留言。
[角色B]我们下期再见！

2. 对话互动要求

- **自然对话流**：使用感叹词、思考停顿（用"..."表示）、打断和接话
- **角色间隔**：角色对话之间要有自然的间隔和停顿，让每个角色的发言都有完整的表达空间，避免对话过于密集
- **角色一致性**：每句台词必须符合角色的性格和说话风格
- **话题过渡**：话题转换要自然平滑，避免生硬切换
- **对话深度**：每段对话要深入展开，包含具体细节、案例分析、个人经历、专业见解等
- **互动频率**：角色之间要有良好的互动，包括提问、回应、补充、质疑、赞同等，但要保持适当的间隔
- **内容充实**：避免简短的回答，每个角色的发言都要有实质性内容，能够推动讨论深入

{scene_requirements}

3. 音效标注（可选）

- 可以使用`<|laughter|>`、`<|sigh|>`、`<|applause|>`等格式标注音效（SoulX-Podcast支持的格式）
- 音效会嵌入在对话内容中，例如：`[角色A]哈哈，这个例子太有意思了！<|laughter|>`

4. 剧本格式要求（SoulX-Podcast兼容格式）

**格式规范**：
- **主要格式**：`[角色名]对话内容`（最简洁，SoulX-Podcast原生格式，强烈推荐）
- **可选格式**：`[角色名]（情绪地）对话内容`（支持情绪标注，但情绪标注是可选的）
- **重要**：不要使用冒号，直接写对话内容
- 每行一个角色的发言，角色之间建议有空行间隔，让对话更清晰
- 角色名称必须使用：{role_list}（不要使用其他名称）
- **对话长度**：生成足够长的对话内容，确保播客时长达到4-5分钟
- **对话数量**：每个角色必须发言至少15-20次，总共至少{num_characters * 15}段对话
- **对话深度**：每段对话内容要充实，每句话至少20-50字，包含具体观点、例子、解释或讨论
- **话题展开**：要充分展开讨论，包含多个子话题、深入分析、案例分享、观点碰撞等
- **角色间隔**：角色对话之间要有自然的间隔，每个角色发言后要有适当的停顿，让对话节奏更舒缓

**重要提示**：
- **正确格式1**：`[角色A]今天天气真好！`（最简洁，SoulX-Podcast原生格式）
- **正确格式2**：`[角色A]（兴奋地）今天天气真好！`（带情绪标注）
- **正确格式**：`[角色A]嗯...这个问题确实很有意思。`（思考停顿用"..."表示）

**音效标注**（可选）：
- 可以使用`<|laughter|>`、`<|sigh|>`等格式标注音效（SoulX-Podcast支持的格式）
- 音效会嵌入在对话内容中，例如：`[角色A]哈哈，这个例子太有意思了！<|laughter|>`

5. 输出格式示例（SoulX-Podcast兼容格式）

**示例1：简洁格式（推荐）**
```
[角色A]嘿，听众朋友们，欢迎回到我们的频道！今天咱们可有个大话题要聊。

[角色B]没错，是关于AI能否真正理解人类的幽默。你说，它能听懂咱们的梗吗？

[角色A]好家伙，上来就挑战高难度！我觉得吧，它现在可能还在学习为什么"香蕉滑倒了"是个笑话。

[角色B]嗯...这个问题确实很有意思。从技术角度看，AI理解幽默的关键在于...

[角色A]哈哈，这个例子太有意思了！<|laughter|>
```

**示例2：带情绪标注格式（可选）**
```
[角色A]（兴奋地）嘿，听众朋友们，欢迎回到我们的频道！今天咱们可有个大话题要聊。

[角色B]（故作神秘地）没错，是关于AI能否真正理解人类的幽默。你说，它能听懂咱们的梗吗？

[角色A]（笑着接话）好家伙，上来就挑战高难度！我觉得吧，它现在可能还在学习为什么"香蕉滑倒了"是个笑话。

[角色B]（思考状）嗯...这个问题确实很有意思。从技术角度看，AI理解幽默的关键在于...

[角色A]（兴奋地）哈哈，这个例子太有意思了！
```

**时长要求**：
- 目标时长：4-5分钟
- 对话总字数：建议1500-2500字（纯对话内容，不含标记）
- 对话段数：至少{num_characters * 15}段（每个角色至少15-20次发言）
- 每段对话：每句话至少20-50字，包含具体观点、例子、解释或讨论
- 内容深度：要充分展开讨论，包含多个子话题、深入分析、案例分享、观点碰撞等

现在请开始生成，直接输出对话内容，不要添加任何其他说明、注释或解释。请确保生成足够长的对话内容以达到4-5分钟的播客时长。"""
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

- **剧本格式**（SoulX-Podcast兼容格式）：
   - **主要格式**：`[角色名]对话内容`（最简洁，SoulX-Podcast原生格式，强烈推荐）
   - **可选格式**：`[角色名]（情绪地）对话内容`（支持情绪标注，但情绪标注是可选的）
   - **重要**：不要使用冒号，直接写对话内容
   - 情绪标注示例：思考状、严肃地、疑惑地、激动地、冷静地等
   - 每行一个角色的发言，角色之间建议有空行间隔，让对话更清晰
   - 角色名称必须使用：{role_list}
   - 每个角色必须发言至少5-7次，总共至少{num_characters * 5}段对话
   - **角色间隔**：角色对话之间要有自然的间隔，每个角色发言后要有适当的停顿，让对话节奏更舒缓

- **证据要求**：
   - {req["evidence"]}
   - 引用要自然融入对话，不要生硬堆砌
   - 可以使用"有研究表明..."、"历史上..."、"从哲学角度看..."等表达

【输出格式示例】（SoulX-Podcast兼容格式）
**示例1：简洁格式（推荐）**
```
[{role_names[0] if len(role_names) > 0 else "角色A"}]当AI能在所有标准化测试中击败我们，我们作为人类，独一无二的价值究竟在哪里？

[{role_names[1] if len(role_names) > 1 else "角色B"}]这个问题确实值得深入探讨。从历史角度看，每次技术革命都会引发类似的身份危机...

[{role_names[0] if len(role_names) > 0 else "角色A"}]但有人会说，情感也许只是复杂的算法。我们如何证明人类的独特性呢？

[{role_names[1] if len(role_names) > 1 else "角色B"}]嗯...这个问题很有意思。从哲学角度看，康德提出了"人是目的，不是工具"的观点...
```

**示例2：带情绪标注格式（可选）**
```
[{role_names[0] if len(role_names) > 0 else "角色A"}]（思考状）当AI能在所有标准化测试中击败我们，我们作为人类，独一无二的价值究竟在哪里？

[{role_names[1] if len(role_names) > 1 else "角色B"}]（严肃地）这个问题确实值得深入探讨。从历史角度看，每次技术革命都会引发类似的身份危机...

[{role_names[0] if len(role_names) > 0 else "角色A"}]（疑惑地）但有人会说，情感也许只是复杂的算法。我们如何证明人类的独特性呢？

[{role_names[1] if len(role_names) > 1 else "角色B"}]（冷静地）嗯...这个问题很有意思。从哲学角度看，康德提出了"人是目的，不是工具"的观点...
```

现在请开始生成，直接输出对话内容，不要添加任何其他说明、注释或解释。"""
        return prompt
    
    def analyze_text_for_podcast(
        self,
        text: str,
        api_client=None
    ) -> Dict[str, Any]:
        """
        使用混元大模型分析文本素材，自动推断播客信息
        
        Args:
            text: 文本素材
            api_client: API客户端实例，如果为None则创建新实例
        
        Returns:
            分析结果字典，包含：
            - podcast_name: 播客名称
            - topic: 本期主题
            - characters: 角色设定列表，每个角色包含 name, personality, speaking_style
            - scene_types: 互动场景类型列表
        """
        if api_client is None:
            from .api_client import get_client
            api_client = get_client()
        
        # 限制文本长度
        text_preview = text[:1000] if len(text) > 1000 else text
        if len(text) > 1000:
            text_preview += "..."
        
        analysis_prompt = f"""请分析以下文本素材，推断出适合制作播客的信息。请以JSON格式返回结果。

文本素材：
{text_preview}

请分析并返回以下信息（JSON格式）：
{{
    "podcast_name": "播客节目名称（根据文本内容推断，如'科技前沿'、'商业观察'等）",
    "topic": "本期播客主题（从文本中提取的核心话题）",
    "characters": [
        {{
            "name": "角色1名称",
            "personality": "性格特点（如：外向幽默、喜欢开玩笑）",
            "speaking_style": "说话风格（如：语速较快，常用网络流行语）"
        }},
        {{
            "name": "角色2名称",
            "personality": "性格特点（如：理性严谨、善于分析）",
            "speaking_style": "说话风格（如：语速平稳，逻辑性强）"
        }}
    ],
    "scene_types": ["互动场景类型（如：接梗玩梗、立场冲突、访谈对话等，可多选）"]
}}

要求：
1. 角色数量建议2-3个
2. 场景类型可以从以下选项中选择：接梗玩梗的轻松交流、立场冲突的激烈辩论、愉快合作的访谈对话、不愉快的质疑访谈
3. 播客名称要简洁有力，符合文本主题
4. 主题要准确概括文本核心内容

请直接返回JSON，不要添加其他说明。"""
        
        try:
            response = api_client.generate_text(
                prompt=analysis_prompt,
                temperature=0.7,
                max_tokens=1500
            )
            
            # 尝试提取JSON
            # 移除可能的markdown代码块标记
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*', '', response)
            response = response.strip()
            
            # 尝试找到JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # 验证和规范化结果
                if not isinstance(result, dict):
                    raise ValueError("分析结果不是字典格式")
                
                # 确保所有字段都存在
                if "podcast_name" not in result:
                    result["podcast_name"] = "本期播客"
                if "topic" not in result:
                    result["topic"] = "讨论主题"
                if "characters" not in result:
                    result["characters"] = []
                if "scene_types" not in result:
                    result["scene_types"] = ["自然互动交流"]
                
                # 确保角色数量在2-3个之间
                if len(result["characters"]) < 2:
                    # 如果角色不足，补充默认角色
                    while len(result["characters"]) < 2:
                        result["characters"].append({
                            "name": f"角色{len(result['characters']) + 1}",
                            "personality": "待定义",
                            "speaking_style": "待定义"
                        })
                elif len(result["characters"]) > 3:
                    result["characters"] = result["characters"][:3]
                
                return result
            else:
                # 如果无法解析JSON，返回默认值
                return {
                    "podcast_name": "本期播客",
                    "topic": "讨论主题",
                    "characters": [
                        {"name": "角色A", "personality": "待定义", "speaking_style": "待定义"},
                        {"name": "角色B", "personality": "待定义", "speaking_style": "待定义"}
                    ],
                    "scene_types": ["自然互动交流"]
                }
        except Exception as e:
            # 分析失败时返回默认值
            print(f"自动分析失败: {str(e)}")
            return {
                "podcast_name": "本期播客",
                "topic": "讨论主题",
                "characters": [
                    {"name": "角色A", "personality": "待定义", "speaking_style": "待定义"},
                    {"name": "角色B", "personality": "待定义", "speaking_style": "待定义"}
                ],
                "scene_types": ["自然互动交流"]
            }
    
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
