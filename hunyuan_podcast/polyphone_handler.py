"""
多音字处理模块
用于处理中文TTS中的多音字问题，确保正确发音
"""
import re
from typing import Dict, List, Tuple


class PolyphoneHandler:
    """多音字处理器"""
    
    # 多音字词典：词语 -> 拼音标注
    # 格式：{词语: 拼音标注}
    # 拼音标注格式：使用方括号标注，如 "转行[zhuan3hang2]"
    POLYPHONE_DICT: Dict[str, str] = {
        # 转行相关
        "转行": "转行[zhuan3hang2]",
        "转行做": "转行做[zhuan3hang2zuo4]",
        "转行了": "转行了[zhuan3hang2le5]",
        "转行后": "转行后[zhuan3hang2hou4]",
        "转行前": "转行前[zhuan3hang2qian2]",
        "转行时": "转行时[zhuan3hang2shi2]",
        "转行到": "转行到[zhuan3hang2dao4]",
        "转行去": "转行去[zhuan3hang2qu4]",
        "转行成为": "转行成为[zhuan3hang2cheng2wei2]",
        "转行成为": "转行成为[zhuan3hang2cheng2wei2]",
        "跨界转行": "跨界转行[kua4jie4zhuan3hang2]",
        "转行创业": "转行创业[zhuan3hang2chuang4ye4]",
        "转行成功": "转行成功[zhuan3hang2cheng2gong1]",
        
        # 其他常见多音字
        "银行": "银行[yin2hang2]",
        "行业": "行业[hang2ye4]",
        "行不行": "行不行[xing2bu4xing2]",
        "行走": "行走[xing2zou3]",
        "行为": "行为[xing2wei2]",
        "行动": "行动[xing2dong4]",
        "银行账户": "银行账户[yin2hang2zhang4hu4]",
        "银行卡": "银行卡[yin2hang2ka3]",
        
        # 长字相关
        "长大": "长大[zhang3da4]",
        "成长": "成长[cheng2zhang3]",
        "长期": "长期[chang2qi1]",
        "长度": "长度[chang2du4]",
        "长短": "长短[chang2duan3]",
        "长高": "长高[zhang3gao1]",
        "长胖": "长胖[zhang3pang4]",
        
        # 重字相关
        "重要": "重要[zhong4yao4]",
        "重新": "重新[chong2xin1]",
        "重复": "重复[chong2fu4]",
        "重量": "重量[zhong4liang4]",
        "重点": "重点[zhong4dian3]",
        "重视": "重视[zhong4shi4]",
        
        # 发字相关
        "发现": "发现[fa1xian4]",
        "发展": "发展[fa1zhan3]",
        "发表": "发表[fa1biao3]",
        "头发": "头发[tou2fa5]",
        "理发": "理发[li3fa4]",
        
        # 行字相关（补充）
        "执行": "执行[zhi2xing2]",
        "进行": "进行[jin4xing2]",
        "实行": "实行[shi2xing2]",
        "举行": "举行[ju3xing2]",
        "旅行": "旅行[lv3xing2]",
        "步行": "步行[bu4xing2]",
        "飞行": "飞行[fei1xing2]",
        "银行": "银行[yin2hang2]",
        "商行": "商行[shang1hang2]",
        "内行": "内行[nei4hang2]",
        "外行": "外行[wai4hang2]",
        "同行": "同行[tong2hang2]",
        
        # 为字相关
        "为了": "为了[wei4le5]",
        "因为": "因为[yin1wei4]",
        "作为": "作为[zuo4wei2]",
        "成为": "成为[cheng2wei2]",
        "认为": "认为[ren4wei2]",
        "以为": "以为[yi3wei2]",
        "行为": "行为[xing2wei2]",
        
        # 处字相关
        "处理": "处理[chu3li3]",
        "处于": "处于[chu3yu2]",
        "到处": "到处[dao4chu4]",
        "好处": "好处[hao3chu4]",
        "坏处": "坏处[huai4chu4]",
        
        # 中字相关
        "中间": "中间[zhong1jian1]",
        "中心": "中心[zhong1xin1]",
        "中国": "中国[zhong1guo2]",
        "中奖": "中奖[zhong4jiang3]",
        "中意": "中意[zhong4yi4]",
        "中毒": "中毒[zhong4du2]",
        
        # 好字相关
        "好人": "好人[hao3ren2]",
        "好事": "好事[hao3shi4]",
        "好学": "好学[hao4xue2]",
        "好客": "好客[hao4ke4]",
        "好胜": "好胜[hao4sheng4]",
        
        # 还字相关
        "还有": "还有[hai2you3]",
        "还是": "还是[hai2shi4]",
        "归还": "归还[gui1huan2]",
        "还钱": "还钱[huan2qian2]",
        "还债": "还债[huan2zhai4]",
        
        # 会字相关
        "会议": "会议[hui4yi4]",
        "会面": "会面[hui4mian4]",
        "会计": "会计[kuai4ji4]",
        "会算": "会算[hui4suan4]",
        
        # 空字相关
        "空气": "空气[kong1qi4]",
        "空间": "空间[kong1jian1]",
        "空白": "空白[kong4bai2]",
        "空闲": "空闲[kong4xian2]",
        
        # 看字相关
        "看见": "看见[kan4jian4]",
        "看书": "看书[kan4shu1]",
        "看护": "看护[kan1hu4]",
        "看守": "看守[kan1shou3]",
        
        # 了字相关
        "了解": "了解[liao3jie3]",
        "了结": "了结[liao3jie2]",
        "了得": "了得[liao3de2]",
        "了了": "了了[liao3liao3]",
        "好了": "好了[hao3le5]",
        "完了": "完了[wan2le5]",
        
        # 没字相关
        "没有": "没有[mei2you3]",
        "没完": "没完[mei2wan2]",
        "淹没": "淹没[yan1mo4]",
        "沉没": "沉没[chen2mo4]",
        
        # 说字相关
        "说话": "说话[shuo1hua4]",
        "说明": "说明[shuo1ming2]",
        "说服": "说服[shuo1fu2]",
        "游说": "游说[you2shui4]",
        
        # 数字相关
        "数学": "数学[shu4xue2]",
        "数字": "数字[shu4zi4]",
        "数数": "数数[shu3shu4]",
        "数一数": "数一数[shu3yi1shu3]",
        
        # 调字相关
        "调整": "调整[tiao2zheng3]",
        "调节": "调节[tiao2jie2]",
        "调查": "调查[diao4cha2]",
        "调动": "调动[diao4dong4]",
        
        # 应字相关
        "应该": "应该[ying1gai1]",
        "应当": "应当[ying1dang1]",
        "应用": "应用[ying4yong4]",
        "应对": "应对[ying4dui4]",
        
        # 正字相关
        "正确": "正确[zheng4que4]",
        "正常": "正常[zheng4chang2]",
        "正月": "正月[zheng1yue4]",
        "正在": "正在[zheng4zai4]",
    }
    
    def __init__(self):
        """初始化多音字处理器"""
        # 按长度排序，优先匹配长词
        self.sorted_phrases = sorted(
            self.POLYPHONE_DICT.keys(),
            key=len,
            reverse=True
        )
    
    def process_text(self, text: str) -> str:
        """
        处理文本中的多音字，添加拼音标注
        
        Args:
            text: 原始文本
            
        Returns:
            处理后的文本（包含拼音标注）
        """
        if not text:
            return text
        
        result = text
        
        # 按长度从长到短匹配，避免短词覆盖长词
        for phrase in self.sorted_phrases:
            if phrase in result:
                # 使用正则表达式确保匹配完整词语（避免部分匹配）
                # 匹配词语边界（中文、英文、数字、标点符号边界）
                pattern = r'(?<![a-zA-Z0-9\u4e00-\u9fff])' + re.escape(phrase) + r'(?![a-zA-Z0-9\u4e00-\u9fff])'
                result = re.sub(pattern, self.POLYPHONE_DICT[phrase], result)
        
        return result
    
    def add_polyphone_to_dict(self, phrase: str, pinyin: str):
        """
        动态添加多音字到词典
        
        Args:
            phrase: 词语
            pinyin: 拼音标注（格式：拼音+声调，如 "zhuan3hang2"）
        """
        # 构建标注格式：词语[拼音]
        annotated = f"{phrase}[{pinyin}]"
        self.POLYPHONE_DICT[phrase] = annotated
        # 重新排序
        self.sorted_phrases = sorted(
            self.POLYPHONE_DICT.keys(),
            key=len,
            reverse=True
        )


# 全局多音字处理器实例
_polyphone_handler = None

def get_polyphone_handler() -> PolyphoneHandler:
    """获取多音字处理器单例"""
    global _polyphone_handler
    if _polyphone_handler is None:
        _polyphone_handler = PolyphoneHandler()
    return _polyphone_handler


