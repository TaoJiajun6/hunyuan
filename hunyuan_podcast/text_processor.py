"""
文本处理模块
实现角色标记解析、对话提取等功能
"""
import re
import json
from typing import List, Dict, Tuple, Optional, Any
from .polyphone_handler import get_polyphone_handler


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
        同时处理多音字，确保正确发音
        
        Args:
            content: 原始对话内容
        
        Returns:
            清理后的对话内容（包含多音字拼音标注）
        """
        if not content:
            return content
        
        # 先处理多音字，添加拼音标注
        polyphone_handler = get_polyphone_handler()
        content = polyphone_handler.process_text(content)
        
        # 移除内容中的音效标注（但不移除拼音标注）
        # 拼音标注格式：词语[拼音]，音效标注格式：[音效：xxx]
        content = re.sub(r'\[音效[：:][^\]]+\]', '', content).strip()
        
        # 移除括号内的动作描述词（如 (点头)、(思考状)、(Nods)、(Thinking) 等）
        # 支持中文括号（）和英文括号()，使用非贪婪匹配
        # 注意：不匹配方括号[]，因为拼音标注使用方括号
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
    
    def build_character_prompt(
        self,
        character_descriptions: Dict[str, Dict[str, str]],
        text_material: Optional[str] = None,
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
        
        # 如果提供了文本素材，使用文本素材；否则使用主题
        if text_material:
            material_text = f"\n【文本素材】\n{text_material}\n\n请基于以上文本素材，让角色进行高度拟人化的互动对话。"
        elif topic:
            material_text = f"\n【播客主题】\n{topic}\n\n请基于以上主题，让角色进行高度拟人化的互动对话。"
        else:
            material_text = "\n【播客内容】\n请根据角色人设自由生成一段高度拟人化的播客对话。"
        
        prompt = f"""【系统指令：高度拟人化角色互动对话生成】

你是一个专业的对话编剧和配音指导。你的任务是根据用户提供的精确角色人设和文本素材，生成一段高度拟人化、真实自然的N角色互动对话。

【用户自定义角色人设】

{character_text}

{material_text}

【核心要求：高度拟人化对话】

**1. 真实对话感（最重要）**
   - 对话必须高度拟人，像真实人类在聊天一样自然
   - 使用大量感叹词、语气词、填充词：如"嗯..."、"啊？"、"呃..."、"啧"、"哈哈！"、"哇塞！"、"天哪！"、"真的假的？"、"那当然了"、"怎么说呢"、"我想想啊"等
   - 角色应该有自然的犹豫、思考、打断、附和、反问等真实反应
   - 允许角色偶尔说错话、重复、纠正自己，体现真实对话的不完美性

**2. 精巧的对话设计**
   - 话题要有自然的流动和转换，不要生硬地切换话题
   - 角色之间的互动要有机衔接，一个角色的话题自然引发另一个角色的反应
   - 对话要有起承转合，包含提问、回答、延伸、转折、总结等环节
   - 角色之间要有情绪上的呼应和共鸣，体现真实的交流感

**3. 自然反应机制**
   - 当角色听到惊讶的内容时，应该用"啊？"、"真的假的？"、"不会吧？"等自然反应
   - 当角色在思考时，应该用"嗯..."、"让我想想"、"这个嘛..."等
   - 当角色表示认同或附和时，应该用"对对对"、"没错"、"就是就是"、"我也觉得"等
   - 当角色提出质疑时，应该用"不过..."、"但是..."、"话说回来..."等

**4. 风格固化**
   - 严格使用符合该角色人设的词汇库和句式结构
   - 根据人设调整句子长度和结构：活泼角色用短句、感叹句，严谨角色用长句、条件句
   - 每个角色的情绪反应必须符合其基本人设
   - 角色之间的互动模式应符合人设关系

**5. 剧本格式**（SoulX-Podcast兼容格式）：
   - **主要格式**：`[角色名]对话内容`（最简洁，SoulX-Podcast原生格式，强烈推荐）
   - **可选格式**：`[角色名]（情绪地）对话内容`（支持情绪标注，但情绪标注是可选的）
   - **重要**：不要使用冒号，直接写对话内容
   - 情绪标注示例：兴奋地、疑惑地、严肃地、开玩笑地、激动地、冷静地、思考状、惊讶地、恍然大悟地等
   - 每行一个角色的发言，角色之间建议有空行间隔，让对话更清晰
   - 角色名称必须使用：{role_list}
   - **角色间隔**：角色对话之间要有自然的间隔，每个角色发言后要有适当的停顿，让对话节奏更舒缓

**6. 多音字使用规范**（重要）：
   - 注意多音字的正确使用，避免产生歧义或读错音
   - 常见多音字示例：
     * "转行"中的"转"读"zhuǎn"（第三声），如"跨界转行"、"转行创业"
     * "银行"中的"行"读"háng"（第二声），如"银行账户"、"银行卡"
     * "行走"中的"行"读"xíng"（第二声），如"行走"、"行为"、"行动"
     * "长大"中的"长"读"zhǎng"（第三声），如"长大"、"长高"
     * "长期"中的"长"读"cháng"（第二声），如"长期"、"长度"
   - 如果遇到不确定读音的多音字，优先使用更常见、更不容易读错的表达方式
   - 避免使用容易产生歧义的多音字组合

**7. 对话要求**：
   - 每个角色必须发言至少6-8次，总共至少{len(role_names) * 6}段对话
   - 对话要自然流畅，角色之间要有良好的互动和回应
   - 必须包含感叹词、语气词、填充词等真实对话元素
   - 对话要有话题的自然流动和转换
   - 每个角色的说话风格要严格符合其角色人设

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
            character_info = "\n2. 角色设定（2-4个角色）\n\n"
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
        
        # 构建完整的提示词（优化后的清晰结构）
        prompt = f"""【核心任务】
你是一位专业的播客编剧和对话导演。请将提供的文本素材转化为一段结构完整、互动自然、符合真人交流方式的多角色播客对话脚本。

【输入信息】

1. 播客基本信息
{final_podcast_info}

2. 角色设定
{character_info}

3. 文本素材
{text_preview}

4. 互动场景类型
{scene_types_str}
{category_section}

【生成要求】

一、播客结构模板

[角色A]大家好，欢迎收听《{podcast_name if podcast_name else "本期播客"}》！我是[角色A名字]。
[角色B]我是[角色B名字]。今天我们要聊一个很有意思的话题：{topic if topic else "[本期主题]"}。
[角色A]没错！说到这个话题，我最近发现...[自然引入主题]

[讨论主体 - 基于文本素材展开，包含多个角度、深入分析、案例分享、观点碰撞，时长约3-4分钟]

[角色C]好了，今天关于{topic if topic else "[本期主题]"}的讨论就到这里。
[角色A]感谢大家的收听！如果有什么想法，欢迎在评论区留言。
[角色B]我们下期再见！

二、对话质量要求

- **自然对话流**：使用感叹词、思考停顿（用"..."表示）、打断和接话
- **角色一致性**：每句台词必须符合角色的性格和说话风格
- **话题过渡**：话题转换要自然平滑，避免生硬切换
- **对话深度**：每段对话要深入展开，包含具体细节、案例分析、个人经历、专业见解
- **互动频率**：角色之间要有良好的互动，包括提问、回应、补充、质疑、赞同等

{scene_requirements}

三、格式规范（SoulX-Podcast兼容）

**基本格式**：
- 主要格式：`[角色名]对话内容`（推荐）
- 可选格式：`[角色名]（情绪地）对话内容`（支持情绪标注）
- 重要：不要使用冒号，直接写对话内容
- 角色名称必须使用：{role_list}

**对话要求**：
- 每个角色发言8-10次，总共约{num_characters * 9}段对话（控制在35-45轮以内）
- 每段对话40-60字，包含具体观点、例子、解释或讨论
- 播客时长约5-6分钟
- 对话总字数建议2000-3000字（纯对话内容）

**音效标注**（可选）：
- 格式：`<|laughter|>`、`<|sigh|>`、`<|applause|>`
- 示例：`[角色A]哈哈，这个例子太有意思了！<|laughter|>`

四、输出示例

**简洁格式（推荐）**：
```
[角色A]嘿，听众朋友们，欢迎回到我们的频道！今天咱们可有个大话题要聊。

[角色B]没错，是关于AI能否真正理解人类的幽默。你说，它能听懂咱们的梗吗？

[角色A]好家伙，上来就挑战高难度！我觉得吧，它现在可能还在学习为什么"香蕉滑倒了"是个笑话。

[角色B]嗯...这个问题确实很有意思。从技术角度看，AI理解幽默的关键在于...
```

现在请开始生成，直接输出对话内容，不要添加任何其他说明、注释或解释。"""
        return prompt
    
    def _generate_example_format(self, role_names: List[str], num_characters: int, with_emotion: bool = False) -> str:
        """
        生成示例格式
        
        Args:
            role_names: 角色名称列表
            num_characters: 角色数量
            with_emotion: 是否包含情绪标注
            
        Returns:
            示例格式字符串
        """
        examples = []
        emotions = ["思考状", "严肃地", "疑惑地", "冷静地", "激动地"]
        
        # 根据角色数量生成示例对话
        if num_characters == 1:
            # 单人播客：角色A的独白式对话
            if with_emotion:
                examples.append(f"[{role_names[0]}]（{emotions[0]}）关于这个主题，我们首先需要思考的是：它的核心问题是什么？")
                examples.append(f"[{role_names[0]}]（{emotions[1]}）这个问题确实值得深入探讨。从历史/理论/实践角度看...")
                examples.append(f"[{role_names[0]}]（{emotions[2]}）但有人可能会提出不同的观点...")
                examples.append(f"[{role_names[0]}]（{emotions[3]}）嗯...这个问题很有意思。从另一个角度看...")
            else:
                examples.append(f"[{role_names[0]}]关于这个主题，我们首先需要思考的是：它的核心问题是什么？")
                examples.append(f"[{role_names[0]}]这个问题确实值得深入探讨。从历史/理论/实践角度看...")
                examples.append(f"[{role_names[0]}]但有人可能会提出不同的观点...")
                examples.append(f"[{role_names[0]}]嗯...这个问题很有意思。从另一个角度看...")
        elif num_characters == 2:
            # 双人对话：角色A和角色B
            if with_emotion:
                examples.append(f"[{role_names[0]}]（{emotions[0]}）关于这个主题，我们首先需要思考的是：它的核心问题是什么？")
                examples.append(f"[{role_names[1]}]（{emotions[1]}）这个问题确实值得深入探讨。从历史/理论/实践角度看...")
                examples.append(f"[{role_names[0]}]（{emotions[2]}）但有人可能会提出不同的观点...")
                examples.append(f"[{role_names[1]}]（{emotions[3]}）嗯...这个问题很有意思。从另一个角度看...")
            else:
                examples.append(f"[{role_names[0]}]关于这个主题，我们首先需要思考的是：它的核心问题是什么？")
                examples.append(f"[{role_names[1]}]这个问题确实值得深入探讨。从历史/理论/实践角度看...")
                examples.append(f"[{role_names[0]}]但有人可能会提出不同的观点...")
                examples.append(f"[{role_names[1]}]嗯...这个问题很有意思。从另一个角度看...")
        else:  # num_characters == 3
            # 三人对话：角色A、角色B和角色C
            if with_emotion:
                examples.append(f"[{role_names[0]}]（{emotions[0]}）关于这个主题，我们首先需要思考的是：它的核心问题是什么？")
                examples.append(f"[{role_names[1]}]（{emotions[1]}）这个问题确实值得深入探讨。从历史/理论/实践角度看...")
                examples.append(f"[{role_names[2]}]（{emotions[2]}）我同意，但我想补充一个不同的视角...")
                examples.append(f"[{role_names[0]}]（{emotions[3]}）嗯...这个问题很有意思。从另一个角度看...")
                examples.append(f"[{role_names[1]}]（{emotions[4]}）确实，这让我们需要重新思考...")
            else:
                examples.append(f"[{role_names[0]}]关于这个主题，我们首先需要思考的是：它的核心问题是什么？")
                examples.append(f"[{role_names[1]}]这个问题确实值得深入探讨。从历史/理论/实践角度看...")
                examples.append(f"[{role_names[2]}]我同意，但我想补充一个不同的视角...")
                examples.append(f"[{role_names[0]}]嗯...这个问题很有意思。从另一个角度看...")
                examples.append(f"[{role_names[1]}]确实，这让我们需要重新思考...")
        
        return "\n\n".join(examples)
    
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

【核心原则】
- **就事论事**：必须严格围绕用户指定的主题展开讨论，不要偏离主题或引入无关内容
- **有依据有见地**：所有观点和论述都要有事实依据、理论支撑或案例佐证，不能空泛议论
- **内容准确合理**：确保基本信息准确，逻辑合理，避免错误信息
- **全面呈现与升华**：既要全面呈现主题的核心内容，又要有深度的升华和思考
- **引发深度思考**：内容要有深度、有价值，能够帮助听众跨越认知和领域门槛，引发深度思考

【主题】
{topic}

【内容深度要求】

请生成的脚本严格围绕上述主题，包含以下层次，以引导听众进行深度思考：

1. **破题与设问**：
   - 开场围绕主题提出一个尖锐的、引人深思的问题，这个问题必须与主题直接相关
   - 问题应该能够立即抓住听众的注意力，引发共鸣，并引导听众思考主题的核心问题
   - 不要使用与主题无关的通用问题，必须紧扣主题本身

2. **多维视角与证据支撑**（{req["perspective_count"]}）：
   - 从多个维度深入探讨主题，维度选择必须与主题相关
   - **历史维度**：如果主题涉及历史背景，可以从历史发展、演变过程等角度分析
   - **理论/学术视角**：引入与主题相关的理论、学术观点或研究成果作为支撑
   - **实践/案例视角**：引用与主题相关的实际案例、数据或实践经验
   - **跨领域视角**：从不同领域（如经济、社会、文化、技术等）的角度分析主题，但必须与主题相关
   - **（关键）呈现对立观点**：脚本中应{req["opposition"]}，或者主持人自我设问，以体现思维的辩证性
   - **重要**：所有视角和观点都必须与主题直接相关，不要引入无关领域的内容

3. **升华与开放性结尾**：
   - {req["ending"]}
   - 不提供简单的"标准答案"，而是梳理讨论的脉络，指出与主题相关的核心问题或矛盾
   - 结尾应引导听众带着与主题相关的新问题离开，而非结束思考
   - 升华部分必须基于主题本身，不要偏离到其他话题

【播客呈现形式】

- **角色设定**：{"建议设置为一位引导性强、知识渊博的主持人（" + role_names[0] + "），进行单人深度播客。" if num_characters == 1 else f"建议设置为一位引导性强、知识渊博的主持人（{role_names[0]}），与{len(role_names)-1}位来自与主题相关的不同领域的嘉宾进行对谈。嘉宾的领域选择必须与主题相关。"}

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
   - 每个角色发言6-8次即可，总共约{num_characters * 7}段对话（控制在30-40轮对话以内，确保播客时长约5-6分钟）
   - **角色间隔**：角色对话之间要有自然的间隔，每个角色发言后要有适当的停顿，让对话节奏更舒缓

- **证据要求**：
   - {req["evidence"]}
   - 引用要自然融入对话，不要生硬堆砌
   - 可以使用"有研究表明..."、"历史上..."、"从XX角度看..."等表达
   - **关键**：所有引用、案例、数据都必须与主题直接相关，确保准确性和相关性

【内容质量要求】
1. **基本信息准确合理**：确保所有事实、数据、案例准确无误，逻辑合理
2. **内容质量高有深度有价值**：内容要有深度，不能流于表面，要有独特的见解和价值
3. **原文内容的全面呈现**：如果主题涉及具体内容或文本，要全面、准确地呈现核心信息
4. **升华内容的丰富有趣**：在全面呈现的基础上，要有深度的升华，使内容更加丰富有趣

【输出格式示例】（SoulX-Podcast兼容格式）

根据角色数量，示例格式如下：

**示例1：简洁格式（推荐）- {num_characters}个角色**
```
{self._generate_example_format(role_names, num_characters, with_emotion=False)}
```

**示例2：带情绪标注格式（可选）- {num_characters}个角色**
```
{self._generate_example_format(role_names, num_characters, with_emotion=True)}
```

**重要提醒**：
- 所有对话内容必须严格围绕主题"{topic}"展开
- 不要引入与主题无关的内容
- 确保内容准确、有依据、有价值
- 就事论事，深入探讨主题本身

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
1. 角色数量建议2-4个
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
                elif len(result["characters"]) > 4:
                    result["characters"] = result["characters"][:4]
                
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
