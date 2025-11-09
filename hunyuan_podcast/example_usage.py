"""
混元AI播客生成系统 - 使用示例
"""
from .podcast_generator import PodcastGenerator


def example_multi_role_podcast():
    """示例1：多角色互动播客"""
    print("=" * 50)
    print("示例1：多角色互动播客")
    print("=" * 50)
    
    # 初始化生成器
    generator = PodcastGenerator()
    
    # 设置角色音色（需要替换为实际的音频文件路径）
    generator.set_role_voice("角色A", "index-tts/examples/voice_01.wav")
    generator.set_role_voice("角色B", "index-tts/examples/voice_02.wav")
    
    # 输入文本（包含角色标记）
    text = """
[角色A]大家好，欢迎收听今天的播客节目。
[角色B]是的，今天我们要聊一个很有趣的话题。
[角色A]没错，让我们开始吧！
[角色B]好的，今天我们要讨论人工智能的发展。
"""
    
    # 生成播客
    output_path = generator.generate_from_text(
        text=text,
        verbose=True
    )
    
    print(f"播客已生成：{output_path}")


def example_character_podcast():
    """示例2：自定义角色播客"""
    print("=" * 50)
    print("示例2：自定义角色播客")
    print("=" * 50)
    
    # 初始化生成器
    generator = PodcastGenerator()
    
    # 定义角色人设
    character_descriptions = {
        "主持人": "一个幽默风趣的主持人，喜欢开玩笑，说话轻松活泼",
        "专家": "一个严谨的AI专家，说话有条理，喜欢深入分析技术问题"
    }
    
    # 设置角色音色
    role_voices = {
        "主持人": "index-tts/examples/voice_01.wav",
        "专家": "index-tts/examples/voice_02.wav"
    }
    
    # 生成播客
    output_path = generator.generate_with_characters(
        character_descriptions=character_descriptions,
        role_voices=role_voices,
        topic="人工智能的未来发展",
        verbose=True
    )
    
    print(f"播客已生成：{output_path}")


def example_deep_podcast():
    """示例3：主题深度播客"""
    print("=" * 50)
    print("示例3：主题深度播客")
    print("=" * 50)
    
    # 初始化生成器
    generator = PodcastGenerator()
    
    # 设置角色音色
    role_voices = {
        "角色A": "index-tts/examples/voice_01.wav",
        "角色B": "index-tts/examples/voice_02.wav"
    }
    
    # 生成深度播客
    output_path = generator.generate_deep_podcast(
        topic="人工智能对人类社会的影响",
        role_voices=role_voices,
        num_characters=2,
        depth_level="深度",
        verbose=True
    )
    
    print(f"播客已生成：{output_path}")


if __name__ == "__main__":
    print("混元AI播客生成系统 - 使用示例")
    print("\n注意：运行示例前请确保：")
    print("1. IndexTTS-2模型文件已下载")
    print("2. 音色参考音频文件存在")
    print("3. API密钥已配置\n")
    
    # 取消注释以运行示例
    # example_multi_role_podcast()
    # example_character_podcast()
    # example_deep_podcast()

