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
    
    # 数字转中文的映射
    DIGIT_TO_CHINESE = {
        '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
        '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'
    }
    
    # 单位映射
    UNITS = ['', '十', '百', '千', '万', '十万', '百万', '千万', '亿']
    
    # 带情绪标注的角色标记：匹配 [角色名]（情绪地）：内容 或 [角色名]（情绪地）内容
    # 也匹配动作描述：[角色名]（思考状）：内容 或 [角色名]（点头）：内容
    ROLE_WITH_EMOTION_PATTERN = re.compile(r'\[([^\]]+)\]\s*（([^）]+)地）\s*[:：]?\s*(.*)')
    
    # 带动作描述的角色标记：匹配 [角色名]（思考状）：内容 或 [角色名]（点头）：内容（不包含"地"字）
    ROLE_WITH_ACTION_PATTERN = re.compile(r'\[([^\]]+)\]\s*[（(]([^）)]+?)[）)]\s*[:：]?\s*(.*)')
    
    def __init__(self):
        """初始化文本处理器"""
        pass
    
    def number_to_chinese(self, num_str: str) -> str:
        """
        将数字字符串转换为中文读音，确保数字读完整、正确
        
        Args:
            num_str: 数字字符串，如 "123", "2024", "3.14" 等
        
        Returns:
            中文读音，如 "一百二十三", "二零二四", "三点一四" 等
        """
        if not num_str:
            return num_str
        
        # 处理小数：确保小数点被正确读作"点"，且连贯不停顿
        if '.' in num_str:
            parts = num_str.split('.')
            if len(parts) == 2:
                integer_part = self._number_to_chinese_integer(parts[0]) if parts[0] else '零'
                # 小数部分逐位转换为中文数字
                decimal_part = ''.join([self.DIGIT_TO_CHINESE.get(d, d) for d in parts[1] if d.isdigit()])
                # 使用零宽连接符（U+200D）确保"点"字前后连贯，TTS不会停顿
                # 格式：整数部分 + 零宽连接符 + "点" + 零宽连接符 + 小数部分
                zwj = '\u200D'  # Zero Width Joiner
                if decimal_part:
                    return f"{integer_part}{zwj}点{zwj}{decimal_part}"
                else:
                    return f"{integer_part}{zwj}点"
        
        # 处理整数
        return self._number_to_chinese_integer(num_str)
    
    def _number_to_chinese_integer(self, num_str: str) -> str:
        """将整数转换为中文读音"""
        if not num_str or not num_str.lstrip('-').isdigit():
            return num_str
        
        is_negative = num_str.startswith('-')
        num_str = num_str.lstrip('-')
        num = int(num_str)
        
        # 0-9 直接转换
        if num < 10:
            result = self.DIGIT_TO_CHINESE[str(num)]
            return '负' + result if is_negative else result
        
        # 10-99
        if num < 100:
            tens = num // 10
            ones = num % 10
            if tens == 1:
                result = '十'
            else:
                result = self.DIGIT_TO_CHINESE[str(tens)] + '十'
            if ones > 0:
                result += self.DIGIT_TO_CHINESE[str(ones)]
            return ('负' + result) if is_negative else result
        
        # 100-999
        if num < 1000:
            hundreds = num // 100
            remainder = num % 100
            result = self.DIGIT_TO_CHINESE[str(hundreds)] + '百'
            if remainder > 0:
                if remainder < 10:
                    result += '零' + self.DIGIT_TO_CHINESE[str(remainder)]
                else:
                    result += self._number_to_chinese_integer(str(remainder))
            return ('负' + result) if is_negative else result
        
        # 1000-9999
        if num < 10000:
            thousands = num // 1000
            remainder = num % 1000
            result = self.DIGIT_TO_CHINESE[str(thousands)] + '千'
            if remainder > 0:
                if remainder < 100:
                    result += '零' + self._number_to_chinese_integer(str(remainder))
                else:
                    result += self._number_to_chinese_integer(str(remainder))
            return ('负' + result) if is_negative else result
        
        # 10000及以上，使用万为单位
        if num < 100000000:  # 小于1亿
            wan = num // 10000
            remainder = num % 10000
            result = self._number_to_chinese_integer(str(wan)) + '万'
            if remainder > 0:
                if remainder < 1000:
                    result += '零' + self._number_to_chinese_integer(str(remainder))
                else:
                    result += self._number_to_chinese_integer(str(remainder))
            return ('负' + result) if is_negative else result
        
        # 1亿及以上
        yi = num // 100000000
        remainder = num % 100000000
        result = self._number_to_chinese_integer(str(yi)) + '亿'
        if remainder > 0:
            if remainder < 10000000:
                result += '零' + self._number_to_chinese_integer(str(remainder))
            else:
                result += self._number_to_chinese_integer(str(remainder))
        return ('负' + result) if is_negative else result
    
    def convert_date_to_chinese(self, date_str: str) -> str:
        """
        将日期字符串转换为中文读音
        
        Args:
            date_str: 日期字符串，如 "2024-11-15", "2024/11/15", "2024年11月15日" 等
        
        Returns:
            中文读音，如 "二零二四年十一月十五日"
        """
        if not date_str:
            return date_str
        
        # 处理标准日期格式：YYYY-MM-DD 或 YYYY/MM/DD
        date_pattern = r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})'
        match = re.match(date_pattern, date_str)
        if match:
            year, month, day = match.groups()
            year_chinese = ''.join([self.DIGIT_TO_CHINESE.get(d, d) for d in year])
            month_chinese = self.number_to_chinese(month)
            day_chinese = self.number_to_chinese(day)
            return f"{year_chinese}年{month_chinese}月{day_chinese}日"
        
        # 处理中文日期格式：2024年11月15日
        date_pattern_cn = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        match = re.match(date_pattern_cn, date_str)
        if match:
            year, month, day = match.groups()
            year_chinese = ''.join([self.DIGIT_TO_CHINESE.get(d, d) for d in year])
            month_chinese = self.number_to_chinese(month)
            day_chinese = self.number_to_chinese(day)
            return f"{year_chinese}年{month_chinese}月{day_chinese}日"
        
        return date_str
    
    def convert_price_to_chinese(self, price_str: str) -> str:
        """
        将价格字符串转换为中文读音
        
        Args:
            price_str: 价格字符串，如 "100元", "¥100", "$100", "100.50元" 等
        
        Returns:
            中文读音，如 "一百元", "一百点五零元" 等
        """
        if not price_str:
            return price_str
        
        # 提取数字部分
        # 匹配：¥100、$100、100元、100.50元、100块等
        price_match = re.match(r'[¥$]?(\d+\.?\d*)[元块]?', price_str)
        if price_match:
            num_str = price_match.group(1)
            chinese_num = self.number_to_chinese(num_str)
            # 判断货币单位
            if '¥' in price_str or '元' in price_str or '块' in price_str:
                return f"{chinese_num}元"
            elif '$' in price_str:
                return f"{chinese_num}美元"
            else:
                return f"{chinese_num}元"
        
        return price_str
    
    def convert_tech_terms_to_chinese(self, text: str) -> str:
        """
        将技术术语中的数字转换为中文读音
        如：USB2.0 -> USB二点零, USB3.0 -> USB三点零, HDMI2.1 -> HDMI二点一, WiFi6 -> WiFi六, 5G -> 五G
        
        Args:
            text: 原始文本
        
        Returns:
            转换后的文本，技术术语中的数字已转换为中文读音
        """
        if not text:
            return text
        
        # 匹配技术术语格式：字母+数字+点+数字（如 USB2.0, HDMI2.1）
        def replace_tech_term_with_dot(match):
            letters = match.group(1)  # 字母部分（如 USB, HDMI）
            num1 = match.group(2)  # 第一个数字（如 2, 3）
            num2 = match.group(3)  # 第二个数字（小数点后，如 0, 1）
            
            num1_chinese = self.number_to_chinese(num1)
            # 小数点后的数字逐位转换
            num2_chinese = ''.join([self.DIGIT_TO_CHINESE.get(d, d) for d in num2])
            # 使用零宽连接符确保"点"字连贯不停顿
            zwj = '\u200D'  # Zero Width Joiner
            return f"{letters}{num1_chinese}{zwj}点{zwj}{num2_chinese}"
        
        # 匹配：字母+数字+点+数字（如 USB2.0, HDMI2.1, USB3.0）
        text = re.sub(r'([A-Za-z]+)(\d+)\.(\d+)', replace_tech_term_with_dot, text)
        
        # 匹配：字母+数字（如 WiFi6, 5G, 4K, WiFi7）
        # 只匹配常见的技术术语格式，避免误匹配
        def replace_tech_term_letters_num(match):
            full_match = match.group(0)
            # 分离字母和数字部分
            letters_match = re.match(r'([A-Za-z]+)(\d+)', full_match)
            if letters_match:
                letters = letters_match.group(1)
                num = letters_match.group(2)
                num_chinese = self.number_to_chinese(num)
                return f"{letters}{num_chinese}"
            return full_match
        
        def replace_tech_term_num_letter(match):
            full_match = match.group(0)
            # 分离数字和字母部分
            num_letter_match = re.match(r'(\d+)([A-Z])', full_match)
            if num_letter_match:
                num = num_letter_match.group(1)
                letter = num_letter_match.group(2)
                num_chinese = self.number_to_chinese(num)
                return f"{num_chinese}{letter}"
            return full_match
        
        # 匹配：字母+数字（不跟点或数字），如 WiFi6, HDMI2
        # 限制：字母部分至少2个字符，确保是技术术语
        text = re.sub(r'([A-Za-z]{2,}\d+)(?![\.\d])', replace_tech_term_letters_num, text)
        # 匹配：数字+字母（如 5G, 4K）
        text = re.sub(r'(\d+[A-Z])(?![\.\d])', replace_tech_term_num_letter, text)
        
        return text
    
    def convert_numbers_to_chinese(self, text: str) -> str:
        """
        将文本中的数字转换为中文读音，包括日期、价格、百分比、技术术语等
        
        Args:
            text: 原始文本
        
        Returns:
            转换后的文本，数字已转换为中文读音
        """
        if not text:
            return text
        
        # 0. 先处理技术术语（如 USB2.0, USB3.0, WiFi6, 5G 等）
        text = self.convert_tech_terms_to_chinese(text)
        
        # 1. 处理日期格式（避免被普通数字匹配）
        # 匹配：2024-11-15、2024/11/15、2024年11月15日
        def replace_date(match):
            date_str = match.group(0)
            return self.convert_date_to_chinese(date_str)
        
        # 匹配标准日期格式
        text = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', replace_date, text)
        # 匹配中文日期格式（如果已经是中文格式，确保数字部分转换）
        text = re.sub(r'(\d{4})年(\d{1,2})月(\d{1,2})日', 
                     lambda m: f"{''.join([self.DIGIT_TO_CHINESE.get(d, d) for d in m.group(1)])}年{self.number_to_chinese(m.group(2))}月{self.number_to_chinese(m.group(3))}日", 
                     text)
        
        # 2. 处理价格格式（在日期之后，避免冲突）
        # 匹配：¥100、$100、100元、100.50元、100块、100.99元等
        def replace_price(match):
            price_str = match.group(0)
            return self.convert_price_to_chinese(price_str)
        
        # 匹配价格：支持 ¥、$ 符号在前，或 元、块 在后
        text = re.sub(r'[¥$]\d+\.?\d*', replace_price, text)  # ¥100, $100
        text = re.sub(r'\d+\.?\d*[元块]', replace_price, text)  # 100元, 100.50块
        
        # 2.5. 处理带单位的金额（如 116.3亿元、50.5万元、10.2千元、5.8百元等）
        def replace_amount_with_unit(match):
            num_str = match.group(1)
            unit = match.group(2)  # 亿元、万元、千元、百元
            chinese_num = self.number_to_chinese(num_str)
            return f"{chinese_num}{unit}"
        
        # 匹配：数字 + 单位（优先匹配亿元、万元、千元、百元，避免与单独的"元"冲突）
        # 注意：这个处理在价格处理之后，所以单独的"元"已经被处理过了
        # 使用非贪婪匹配，优先匹配更长的单位（如"亿元"优先于"元"）
        text = re.sub(r'(\d+\.?\d*)(亿元|万元|千元|百元)', replace_amount_with_unit, text)
        
        # 3. 处理百分比：如 50% -> 百分之五十，87% -> 百分之八十七
        # 使用更精确的正则表达式，确保匹配到百分比符号前的数字
        def replace_percent(match):
            num_str = match.group(1)
            # 确保数字字符串不为空
            if not num_str:
                return match.group(0)  # 如果匹配失败，返回原字符串
            chinese_num = self.number_to_chinese(num_str)
            return f"百分之{chinese_num}"
        
        # 使用更精确的正则表达式，确保匹配数字和百分号
        # 匹配模式：数字（可能包含小数点）+ 百分号，前后可以有空格
        text = re.sub(r'(\d+\.?\d*)\s*%', replace_percent, text)
        
        # 4. 处理普通数字（整数和小数，包括负数）
        # 但排除已经在日期、价格、百分比中的数字
        def replace_number(match):
            num_str = match.group(0)
            start_pos = match.start()
            end_pos = match.end()
            
            # 跳过角色标记中的数字（如 [角色1]）
            if start_pos > 0 and text[start_pos - 1] == '[':
                return num_str
            if end_pos < len(text) and text[end_pos] == ']':
                return num_str
            
            # 检查是否已经在日期、价格、百分比、技术术语中（通过检查前后字符）
            # 如果前后有年、月、日、元、块、%、字母等，说明已经被处理过，跳过
            if start_pos > 0:
                prev_char = text[start_pos - 1]
                # 如果前一个字符是字母，可能是技术术语（如 USB2.0），跳过
                if prev_char.isalpha():
                    return num_str
                if prev_char in '年月日¥$元块%':
                    return num_str
            if end_pos < len(text):
                next_char = text[end_pos]
                # 如果下一个字符是字母或点，可能是技术术语，跳过
                if next_char.isalpha() or next_char == '.':
                    return num_str
                if next_char in '年月日¥$元块%':
                    return num_str
                # 如果下一个字符是"万"、"千"、"百"，后面可能跟着"元"，说明已经被处理过，跳过
                if next_char in '万千百' and end_pos + 1 < len(text) and text[end_pos + 1] == '元':
                    return num_str
            
            return self.number_to_chinese(num_str)
        
        # 匹配整数和小数（包括负数），但排除已经在其他格式中的数字
        text = re.sub(r'-?\d+\.?\d*', replace_number, text)
        
        return text
    
    def clean_dialogue_content(self, content: str) -> str:
        """
        清理对话内容，移除可能误包含的情绪描述词和动作描述
        并将数字转换为中文读音，确保数字读完整、正确
        
        Args:
            content: 原始对话内容
        
        Returns:
            清理后的对话内容，数字已转换为中文读音
        """
        if not content:
            return content
        
        # 先将数字转换为中文读音
        content = self.convert_numbers_to_chinese(content)
        
        # 移除省略号（...），因为会导致TTS输出错误
        # 将连续的多个点（2个或以上）替换为空字符串
        content = re.sub(r'\.{2,}', '', content)
        
        # 移除内容中的音效标注
        # 音效标注格式：[音效：xxx]
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
    
    def split_dialogue_by_punctuation(self, content: str) -> List[str]:
        """
        根据标点符号将对话内容拆分成多个句子，增强断句效果
        
        Args:
            content: 对话内容
        
        Returns:
            拆分后的句子列表
        """
        if not content:
            return []
        
        # 清理内容
        content = self.clean_dialogue_content(content)
        
        # 如果内容很短或没有明显的标点，直接返回
        if len(content) < 10:
            return [content] if content else []
        
        # 定义句子结束标点（中文和英文）
        sentence_endings = r'[。！？.!?]'
        
        # 按句子结束标点拆分，但保留标点
        sentences = re.split(f'({sentence_endings})', content)
        
        # 合并标点和前面的内容
        result = []
        i = 0
        while i < len(sentences):
            sentence = sentences[i].strip()
            if not sentence:
                i += 1
                continue
            
            # 如果下一个元素是标点，合并
            if i + 1 < len(sentences) and re.match(sentence_endings, sentences[i + 1]):
                sentence += sentences[i + 1]
                i += 2
            else:
                i += 1
            
            if sentence:
                result.append(sentence)
        
        # 如果没有拆分出多个句子，返回原内容
        if len(result) <= 1:
            return [content] if content else []
        
        return result
    
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
                
                # 过滤掉无效的角色名
                if not role_name or len(role_name) == 1 and (role_name.isdigit() or role_name.isalpha()):
                    continue
                if role_name.isdigit() or role_name.startswith('Content_') or not role_name.isprintable():
                    continue
                
                emotion = emotion_match.group(2).strip()
                content = emotion_match.group(3).strip()
                
                # 清理对话内容，移除可能误包含的情绪描述词和音效标注
                content = self.clean_dialogue_content(content)
                
                # 如果角色改变，保存之前的对话
                if current_role and current_role != role_name:
                    if current_content:
                        full_content = ' '.join(current_content)
                        # 根据标点拆分对话，增强断句效果
                        sentences = self.split_dialogue_by_punctuation(full_content)
                        for sentence in sentences:
                            if sentence.strip():
                                dialogues.append((current_role, sentence.strip()))
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
                
                # 过滤掉无效的角色名
                if not role_name or len(role_name) == 1 and (role_name.isdigit() or role_name.isalpha()):
                    continue
                if role_name.isdigit() or role_name.startswith('Content_') or not role_name.isprintable():
                    continue
                
                action = action_match.group(2).strip()
                content = action_match.group(3).strip()
                
                # 清理对话内容，移除可能误包含的动作描述词和音效标注
                content = self.clean_dialogue_content(content)
                
                # 如果角色改变，保存之前的对话
                if current_role and current_role != role_name:
                    if current_content:
                        full_content = ' '.join(current_content)
                        # 根据标点拆分对话，增强断句效果
                        sentences = self.split_dialogue_by_punctuation(full_content)
                        for sentence in sentences:
                            if sentence.strip():
                                dialogues.append((current_role, sentence.strip()))
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
                
                # 过滤掉无效的角色名（纯数字、单个字符、PDF结构标记等）
                if not role_name:
                    continue
                # 过滤掉单个字符（数字或字母，通常是页码或编号）
                if len(role_name) == 1 and (role_name.isdigit() or role_name.isalpha()):
                    continue
                # 过滤掉纯数字（可能是页码）
                if role_name.isdigit():
                    continue
                # 过滤掉PDF/Word文档结构标记
                if role_name.startswith('Content_') or role_name.startswith('content_'):
                    continue
                if role_name in ['XML', 'xml', 'DOCX', 'docx', 'DOC', 'doc', 'PDF', 'pdf']:
                    continue
                # 过滤掉不可打印字符
                if not role_name.isprintable() or '\x00' in role_name:
                    continue
                
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
                        full_content = ' '.join(current_content)
                        # 根据标点拆分对话，增强断句效果
                        sentences = self.split_dialogue_by_punctuation(full_content)
                        for sentence in sentences:
                            if sentence.strip():
                                dialogues.append((current_role, sentence.strip()))
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
            full_content = ' '.join(current_content)
            # 根据标点拆分对话，增强断句效果
            sentences = self.split_dialogue_by_punctuation(full_content)
            for sentence in sentences:
                if sentence.strip():
                    dialogues.append((current_role, sentence.strip()))
        
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

            # 过滤掉纯数字或单个字符的角色（通常是PDF页码、章节编号等）
            # 例如：[1], [2], [J], [A] 等
            if len(role) == 1:
                # 单个字符：如果是纯数字或单个字母，很可能是页码或编号，跳过
                if role.isdigit() or role.isalpha():
                    continue
            
            # 过滤掉纯数字的角色（例如：[123], [456] 等，可能是页码）
            if role.isdigit():
                continue
            
            # 过滤掉常见的PDF/Word文档结构标记
            if role.startswith('Content_') or role.startswith('content_'):
                continue
            if role in ['XML', 'xml', 'DOCX', 'docx', 'DOC', 'doc', 'PDF', 'pdf']:
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
        topic: Optional[str] = None,
        instruction: Optional[str] = None
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
            instruction: 用户指令（可选），用于控制播客生成过程，如"生成1分钟播客"、"使用轻松风格"等，必须严格按照指令执行
        
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
        
        # 构建用户指令规则文本（避免在 f-string 表达式中使用反斜杠）
        instruction_rule_text = ""
        if instruction:
            instruction_rule_text = "** 用户指令执行规则**：\n- 必须严格按照用户指令执行，特别是关于内容要求、时长要求、风格要求等\n- 如果指令中指定了时长（如\"1分钟\"、\"5分钟\"等），必须严格按照该时长生成相应长度的对话内容\n- 如果指令中指定了内容要求（如\"简短\"、\"详细\"等），必须严格按照要求执行\n- 用户指令的优先级高于默认设置，必须优先满足指令要求\n\n"
        
        # 构建用户指令详细文本（避免在 f-string 表达式中使用反斜杠）
        instruction_detail_text = ""
        if instruction:
            instruction_detail_text = f"\n【用户指令】\n\n{instruction}\n\n** 重要**：必须严格按照上述用户指令执行，特别是关于内容要求、时长要求、风格要求等。如果指令中指定了时长（如\"1分钟\"、\"5分钟\"等），必须严格按照该时长生成相应长度的对话内容。如果指令中指定了内容要求（如\"简短\"、\"详细\"等），必须严格按照要求执行。"
        
        prompt = f"""【系统指令：高度拟人化角色互动对话生成】

你是一个专业的对话编剧和配音指导。你的任务是根据用户提供的精确角色人设和文本素材，生成一段高度拟人化、真实自然的N角色互动对话。

{instruction_rule_text}
【用户自定义角色人设】

{character_text}

{material_text}
{instruction_detail_text}
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
   - **角色名称必须严格使用**：{role_list}（不能使用其他名称，如数字、字母等）
   - **禁止使用**：不能使用纯数字（如[1]、[2]）、单个字母（如[J]、[A]）或其他非标准角色名
   - **角色间隔**：角色对话之间要有自然的间隔，每个角色发言后要有适当的停顿，让对话节奏更舒缓

**6. 对话要求**：
   - 每个角色必须发言至少6-8次，总共至少{len(role_names) * 6}段对话
   - 对话要自然流畅，角色之间要有良好的互动和回应
   - 必须包含感叹词、语气词、填充词等真实对话元素
   - 对话要有话题的自然流动和转换
   - 每个角色的说话风格要严格符合其角色人设

**7. 输出格式示例**（SoulX-Podcast兼容格式）：
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
        category: Optional[str] = None,
        instruction: Optional[str] = None
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
            category: 播客分类（可选），如：社会文化与历史、音乐、影视、书、喜剧/脱口秀、艺术、宗教与灵修、科学与科技、时尚与美妆、健康、健身与养身、育儿与家庭、情感、生活、体育运动、休闲娱乐与爱好、商业与财经、新闻、职场万象、自我成长与自愈、学术研究等
            instruction: 用户指令（可选），用于控制播客生成过程，如"生成1分钟播客"、"使用轻松风格"等，必须严格按照指令执行
        
        Returns:
            构建的提示词
        """
        # 限制文本长度，避免提示词过长（增加到2000字符以支持更长的文本）
        text_preview = text[:2000] if len(text) > 2000 else text
        if len(text) > 2000:
            text_preview += "..."
        
        role_names = ["角色A", "角色B", "角色C"][:num_characters]
        role_list = "、".join(role_names)
        
        # 提取角色虚拟名字（用于自我介绍）
        role_virtual_names = []
        has_all_names = True  # 标记是否所有角色都有名字
        
        if character_descriptions:
            for i, role_key in enumerate(role_names):
                # 从角色描述中提取名字，优先使用角色描述中的name字段
                virtual_name = None
                
                if role_key in character_descriptions:
                    role_desc = character_descriptions[role_key]
                    if isinstance(role_desc, dict):
                        virtual_name = role_desc.get("name", "")
                        if virtual_name and virtual_name.strip():
                            virtual_name = virtual_name.strip()
                        else:
                            virtual_name = None
                else:
                    # 如果角色描述中没有对应的键，尝试按顺序获取
                    desc_list = list(character_descriptions.values())
                    if i < len(desc_list):
                        role_desc = desc_list[i]
                        if isinstance(role_desc, dict):
                            virtual_name = role_desc.get("name", "")
                            if virtual_name and virtual_name.strip():
                                virtual_name = virtual_name.strip()
                            else:
                                virtual_name = None
                
                if virtual_name:
                    role_virtual_names.append(virtual_name)
                else:
                    role_virtual_names.append(None)  # 标记需要自动生成
                    has_all_names = False
        else:
            # 如果没有角色描述，所有名字都需要自动生成
            role_virtual_names = [None] * num_characters
            has_all_names = False
        
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
            character_info += f"**重要说明**：以下角色名称仅用于描述角色特征，但在对话标记中必须使用标准角色名（{role_list}），不能使用文本素材中的人名或其他名称。\n\n"
            for i, (role, desc) in enumerate(character_descriptions.items(), 1):
                if i > num_characters:
                    break
                name = desc.get("name", role)
                personality = desc.get("personality", "")
                speaking_style = desc.get("speaking_style", "")
                character_info += f"{role_names[i-1]}（角色名称：{name}）\n"
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
            character_info += f"\n**重要**：即使文本素材中有人名，也必须使用标准角色名（{role_list}）作为对话标记，不能使用文本素材中的人名。\n"
        
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
        
        # 构建用户指令规则文本（避免在 f-string 表达式中使用反斜杠）
        instruction_rule_text_short = ""
        if instruction:
            instruction_rule_text_short = "### 用户指令执行规则\n- 必须严格按照用户指令执行，特别是关于时长、内容和风格要求\n- 用户指令优先级高于默认设置\n"
        
        # 构建场景类型字符串
        scene_types_str = ', '.join(scene_types) if scene_types else "自然互动交流"
        
        # 构建分类相关的指导信息
        category_section = ""
        if category:
            # 根据分类提供具体指导
            category_styles = {
                "社会文化与历史": "注重社会现象、文化内涵、历史事件、人物故事、历史背景，语言优雅有深度，要有文化底蕴和故事性",
                "音乐": "注重音乐赏析、音乐文化、音乐创作、音乐历史，语言优雅有趣，要有艺术性和感染力",
                "影视": "注重剧情分析、角色解读、影视文化、影视评论，语言生动有趣，可以引用经典台词",
                "书": "注重书籍推荐、阅读心得、文学赏析、读书感悟，语言优雅有深度，要有文化底蕴和启发性",
                "喜剧/脱口秀": "注重趣味性、轻松幽默、话题性、幽默搞笑、喜剧表演、轻松对话，语言活泼有趣，节奏可以更快，要有趣味性和娱乐性",
                "艺术": "注重艺术赏析、艺术创作、艺术文化、艺术历史，语言优雅有深度，要有艺术性和感染力",
                "宗教与灵修": "注重精神探索、心灵成长、宗教文化、哲学思辨，语言深刻优雅，要有深度和启发性",
                "科学与科技": "注重技术原理、科学原理、科学发现、发展趋势、创新应用，保持专业性和前瞻性，语言清晰准确、易懂",
                "时尚与美妆": "注重时尚趋势、美妆技巧、穿搭建议、时尚文化，语言时尚有趣，要有实用性和美观性",
                "健康、健身与养身": "注重健康知识、养生方法、疾病预防、运动技巧、健身方法、训练计划，语言温和专业、积极向上，要有科学性和实用性、激励性和可操作性",
                "育儿与家庭": "注重育儿知识、教育方法、亲子关系、家庭生活，语言温和耐心，要有实用性和可操作性",
                "情感": "注重情感分析、情感故事、情感共鸣、情感表达，语言温暖真诚，要有共鸣感和代入感",
                "生活": "注重生活技巧、生活态度、生活分享、生活感悟，语言轻松有趣，要有实用性和共鸣感",
                "体育运动": "注重体育赛事、运动技巧、体育文化、运动健康，语言激情有力，要有竞争性和观赏性",
                "休闲娱乐与爱好": "注重兴趣爱好、休闲活动、娱乐方式、生活乐趣，语言轻松有趣，要有趣味性和娱乐性",
                "商业与财经": "注重商业逻辑、市场分析、商业模式、创业经验、经济分析、投资理财、市场趋势，使用专业术语但要通俗易懂，对话要有深度和实用性",
                "新闻": "注重事实陈述、多角度分析、时效性，保持客观中立，语言简洁明了",
                "职场万象": "注重职场经验、人际关系、沟通技巧、人际交往、职场情商、职业发展、求职技巧、职业规划、面试经验，语言实用接地气，要有真实感和代入感、场景感和实用性",
                "自我成长与自愈": "注重心理分析、行为解读、成长故事、情感共鸣、心理应用、自我疗愈，语言温暖治愈、专业易懂，要有启发性和正能量",
                "学术研究": "注重学术探讨、研究方法、学术观点、知识讲解、学习方法、学习技巧，语言清晰易懂、严谨清晰，要有实用性和可操作性、逻辑严密"
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
# 播客脚本生成指令

## 核心身份
你是一位专业的播客编剧和对话导演。

## 核心任务
将提供的文本素材转化为一段结构完整、互动自然的多角色播客对话脚本。

## 关键规则

### 角色命名规则（必须严格遵守）
- **对话标记必须使用**：{role_list}
- **绝对禁止使用**：文本素材中的任何人名、角色名或实体名称
- 文本素材中的名称仅用于理解内容，对话时必须映射到标准角色名

{instruction_rule_text_short if instruction else ""}

## 输入信息
- **播客信息**：{final_podcast_info}
- **角色设定**：{character_info}
- **文本素材**：{text_preview}
- **互动场景**：{scene_types_str}
{f"- **用户指令**：{instruction}" if instruction else ""}

## 生成要求

### 1. 播客结构
**开场自我介绍必须使用虚拟名字**：
{chr(10).join([f"- {role_names[i]} → {role_virtual_names[i] if role_virtual_names[i] else '[请根据角色设定自动生成合适的虚拟名字]'}" for i in range(num_characters)])}

{f"**⚠️ 重要**：以上标记为'[请根据角色设定自动生成合适的虚拟名字]'的角色，你必须根据该角色的性格、身份、说话风格等特点，自动生成一个合适的、具体的虚拟名字（如：小明、李华、张伟、王芳等常见中文名字，或根据角色特点生成更贴合的名字）。不能使用'主持人A'、'主持人B'这种编号式的名字，必须使用具体的、真实的名字。" if not has_all_names else ""}

**标准结构**：

[开场] 自我介绍（使用虚拟名字）+ 主题引入
[主体] 基于文本素材的深入讨论（3-4分钟）
[结尾] 总结 + 结束语


### 2. 对话质量
- **真实感**：口语化表达、自然停顿、感叹词、即兴反应
- **互动性**：打断、接话、抢话、观点碰撞
- **角色一致**：台词符合角色性格和说话风格
- **内容丰富**：具体细节、案例分析、个人经历、专业见解

### 3. 格式规范
**基本格式**：`[角色名]（情绪地）对话内容`
**禁止使用**：冒号、文本素材中的名称、非标准角色名

**技术参数**：
- 每个角色发言10-12次
- 总对话30-40轮
- 时长5-7分钟
- 总字数2500-3500字

**音效标注**（可选）：`<|laughter|>`、`<|sigh|>`、`<|applause|>`

## 输出示例
[角色A]嘿，听众朋友们，欢迎回来！我是{role_virtual_names[0] if role_virtual_names[0] else '[虚拟名字]'}。
{chr(10) + f"[角色B]我是{role_virtual_names[1] if role_virtual_names[1] else '[虚拟名字]'}。今天我们要聊一个很有意思的话题..." if num_characters >= 2 else ""}
[角色A]好家伙，上来就挑战高难度！我觉得吧...
{chr(10) + "[角色B]嗯...这个问题确实很有深度，从技术角度看..." if num_characters >= 2 else ""}

## 最后提醒
1. 对话标记**必须使用**：{role_list}
2. 开场自我介绍时，必须使用具体的虚拟名字（如：小明、李华、张伟等），不能使用"主持人A"、"主持人B"这种编号式的名字
{f"3. 对于没有提供名字的角色，请根据角色设定自动生成合适的虚拟名字" if not has_all_names else "3. 使用提供的虚拟名字进行自我介绍"}
4. 直接输出对话内容，不添加任何说明

现在请开始生成播客脚本。"""
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
        num_characters: int = 2,
        instruction: Optional[str] = None
    ) -> str:
        """
        构建深度播客生成的提示词
        
        Args:
            topic: 播客主题
            depth_level: 深度级别（深度/中等/浅层）
            num_characters: 角色数量
            instruction: 用户指令（可选），用于控制播客生成过程，如"生成1分钟播客"、"使用轻松风格"等，必须严格按照指令执行
        
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
                "ending": "开放式结尾，引导听众继续思考，不提供标准答案",
                "duration": "8-10分钟",
                "dialogue_count": "每个角色发言10-12次，总共约{num_characters * 11}段对话（控制在50-60轮对话以内）",
                "content_length": "对话总字数建议4000-5000字（纯对话内容，确保内容充实）"
            },
            "中等": {
                "perspective_count": "至少3-4个不同维度",
                "evidence": "应引用相关的理论、案例或研究",
                "opposition": "可以包含不同观点或设问",
                "ending": "可以有一定结论，但也留有思考空间",
                "duration": "5-7分钟",
                "dialogue_count": "每个角色发言8-10次，总共约{num_characters * 9}段对话（控制在40-50轮对话以内）",
                "content_length": "对话总字数建议3000-4000字（纯对话内容，确保内容充实）"
            },
            "浅层": {
                "perspective_count": "至少2-3个不同维度",
                "evidence": "可以提及相关的例子或观点",
                "opposition": "可以简单提及不同观点",
                "ending": "可以有明确的结论或总结",
                "duration": "3-5分钟",
                "dialogue_count": "每个角色发言6-8次，总共约{num_characters * 7}段对话（控制在30-40轮对话以内）",
                "content_length": "对话总字数建议2000-3000字（纯对话内容，确保内容充实）"
            }
        }
        
        req = depth_requirements.get(depth_level, depth_requirements["中等"])
        
        # 处理 dialogue_count 中的表达式，先计算值再格式化
        dialogue_count_text = req["dialogue_count"]
        # 替换表达式 {num_characters * 11} 等为实际计算值
        import re
        def replace_expression(match):
            expr = match.group(1)  # 获取表达式部分，如 "num_characters * 11"
            try:
                # 在安全的环境中计算表达式
                result = eval(expr, {"num_characters": num_characters})
                return str(result)
            except:
                return match.group(0)  # 如果计算失败，返回原字符串
        
        # 匹配 {num_characters * 11} 这样的表达式
        dialogue_count_text = re.sub(r'\{([^}]+)\}', replace_expression, dialogue_count_text)
        
        # 构建用户指令规则文本（避免在 f-string 表达式中使用反斜杠）
        instruction_rule_text_deep = ""
        if instruction:
            instruction_rule_text_deep = "**⚠️ 用户指令执行规则**：\n- 必须严格按照用户指令执行，特别是关于内容要求、时长要求、风格要求等\n- 如果指令中指定了时长（如\"1分钟\"、\"5分钟\"等），必须严格按照该时长生成相应长度的对话内容\n- 如果指令中指定了内容要求（如\"简短\"、\"详细\"等），必须严格按照要求执行\n- 用户指令的优先级高于默认设置，必须优先满足指令要求\n\n"
        
        # 构建用户指令详细文本（避免在 f-string 表达式中使用反斜杠）
        instruction_detail_text_deep = ""
        if instruction:
            instruction_detail_text_deep = f"\n【用户指令】\n\n{instruction}\n\n**⚠️ 重要**：必须严格按照上述用户指令执行，特别是关于内容要求、时长要求、风格要求等。如果指令中指定了时长（如\"1分钟\"、\"5分钟\"等），必须严格按照该时长生成相应长度的对话内容。如果指令中指定了内容要求（如\"简短\"、\"详细\"等），必须严格按照要求执行。"
        
        prompt = f"""【系统指令：深度内容架构师】

你是一档知名深度访谈播客的主编和首席研究员。请围绕用户指定的主题，生成一份有深度、有见地、能引发听众长期思考的播客脚本。

{instruction_rule_text_deep}
【核心原则】
- **就事论事**：必须严格围绕用户指定的主题展开讨论，不要偏离主题或引入无关内容
- **有依据有见地**：所有观点和论述都要有事实依据、理论支撑或案例佐证，不能空泛议论
- **内容准确合理**：确保基本信息准确，逻辑合理，避免错误信息
- **全面呈现与升华**：既要全面呈现主题的核心内容，又要有深度的升华和思考
- **引发深度思考**：内容要有深度、有价值，能够帮助听众跨越认知和领域门槛，引发深度思考

【主题】
{topic}
{instruction_detail_text_deep}
【内容深度要求】

请生成的脚本严格围绕上述主题，包含以下层次，以引导听众进行深度思考：

1. **破题与设问**：
   - 开场围绕主题提出一个尖锐的、引人深思的问题，这个问题必须与主题直接相关
   - 问题应该能够立即抓住听众的注意力，引发共鸣，并引导听众思考主题的核心问题

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
   - **角色名称必须严格使用**：{role_list}（不能使用其他名称，如数字、字母等）
   - **禁止使用**：不能使用纯数字（如[1]、[2]）、单个字母（如[J]、[A]）或其他非标准角色名
   - {dialogue_count_text}，确保播客时长约{req["duration"]}
   - {req["content_length"]}
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
