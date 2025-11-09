## API documentationhttp://localhost:7861/API Recorder3 API endpoints 



Choose one of the following ways to interact with the API.

1. Install the python client ([docs](https://www.gradio.app/guides/getting-started-with-the-python-client)) if you don't already have it installed.

```
copy
$ pip install gradio_client
```

2. Find the API endpoint below corresponding to your desired function in the app. Copy the code snippet, replacing the placeholder values with your own input data. Or use the API Recorder to automatically generate your API requests.

### API name: /wrap_multi_role_podcast 包装函数，格式化脚本输出

```
copyfrom gradio_client import Client, handle_file

	client = Client("http://localhost:7861/")
	result = client.predict(
			text="中科曙光发布640卡超节点，算力密度提升20倍。在2025世界互联网大会乌镇峰会上，中科曙光正式发布全球首款单机柜级640卡超节点scaleX640。这款基于开放系统硬件架构打造的产品，采用一拖二高密架构设计，实现单机柜内640张加速卡的超高速互连，算力密度较同类产品提升20倍。",
			role_a_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			role_b_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			role_c_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			silence_interval=300,
			api_name="/wrap_multi_role_podcast"
	)
	print(result)
```

#### Accepts 5 parameters:

------

text str Default: "中科曙光发布640卡超节点，算力密度提升20倍。在2025世界互联网大会乌镇峰会上，中科曙光正式发布全球首款单机柜级640卡超节点scaleX640。这款基于开放系统硬件架构打造的产品，采用一拖二高密架构设计，实现单机柜内640张加速卡的超高速互连，算力密度较同类产品提升20倍。"

The input value that is provided in the "播客文本（可直接输入普通文本，系统会自动转换为多角色对话）" Textbox component.

------

role_a_voice filepath **Required**

The input value that is provided in the "角色A音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

role_b_voice filepath **Required**

The input value that is provided in the "角色B音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

role_c_voice filepath **Required**

The input value that is provided in the "角色C音色（可选，可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

silence_interval float Default: 300

The input value that is provided in the "角色切换静音间隔（毫秒）" Slider component.

#### Returns tuple of 3 elements

------

[0] filepath

The output value that appears in the "播客音频" Audio component.

------

[1] str

The output value that appears in the "状态信息" Textbox component.

------

[2] str

The output value that appears in the "脚本内容" Html component.

### API name: /wrap_character_podcast 包装函数，格式化脚本输出

```
copyfrom gradio_client import Client, handle_file

	client = Client("http://localhost:7861/")
	result = client.predict(
			character_a_name="角色A",
			character_a_identity="Hello!!",
			character_a_personality="Hello!!",
			character_a_catchphrase="Hello!!",
			character_a_speaking_style="Hello!!",
			character_a_relationship="Hello!!",
			character_a_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			character_b_name="角色B",
			character_b_identity="Hello!!",
			character_b_personality="Hello!!",
			character_b_catchphrase="Hello!!",
			character_b_speaking_style="Hello!!",
			character_b_relationship="Hello!!",
			character_b_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			character_c_name="角色C",
			character_c_identity="Hello!!",
			character_c_personality="Hello!!",
			character_c_catchphrase="Hello!!",
			character_c_speaking_style="Hello!!",
			character_c_relationship="Hello!!",
			character_c_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			topic="Hello!!",
			api_name="/wrap_character_podcast"
	)
	print(result)
```

#### Accepts 22 parameters:

------

character_a_name str Default: "角色A"

The input value that is provided in the "角色A名称" Textbox component.

------

character_a_identity str **Required**

The input value that is provided in the "角色A身份/职业" Textbox component.

------

character_a_personality str **Required**

The input value that is provided in the "角色A核心性格" Textbox component.

------

character_a_catchphrase str **Required**

The input value that is provided in the "角色A口头禅/说话习惯" Textbox component.

------

character_a_speaking_style str **Required**

The input value that is provided in the "角色A说话风格" Textbox component.

------

character_a_relationship str **Required**

The input value that is provided in the "角色A与其他角色的关系" Textbox component.

------

character_a_voice filepath **Required**

The input value that is provided in the "角色A音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

character_b_name str Default: "角色B"

The input value that is provided in the "角色B名称" Textbox component.

------

character_b_identity str **Required**

The input value that is provided in the "角色B身份/职业" Textbox component.

------

character_b_personality str **Required**

The input value that is provided in the "角色B核心性格" Textbox component.

------

character_b_catchphrase str **Required**

The input value that is provided in the "角色B口头禅/说话习惯" Textbox component.

------

character_b_speaking_style str **Required**

The input value that is provided in the "角色B说话风格" Textbox component.

------

character_b_relationship str **Required**

The input value that is provided in the "角色B与其他角色的关系" Textbox component.

------

character_b_voice filepath **Required**

The input value that is provided in the "角色B音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

character_c_name str Default: "角色C"

The input value that is provided in the "角色C名称" Textbox component.

------

character_c_identity str **Required**

The input value that is provided in the "角色C身份/职业" Textbox component.

------

character_c_personality str **Required**

The input value that is provided in the "角色C核心性格" Textbox component.

------

character_c_catchphrase str **Required**

The input value that is provided in the "角色C口头禅/说话习惯" Textbox component.

------

character_c_speaking_style str **Required**

The input value that is provided in the "角色C说话风格" Textbox component.

------

character_c_relationship str **Required**

The input value that is provided in the "角色C与其他角色的关系" Textbox component.

------

character_c_voice filepath **Required**

The input value that is provided in the "角色C音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

topic str **Required**

The input value that is provided in the "播客主题（可选，如果留空则根据角色人设自由生成对话）" Textbox component.

#### Returns tuple of 3 elements

------

[0] filepath

The output value that appears in the "播客音频" Audio component.

------

[1] str

The output value that appears in the "状态信息" Textbox component.

------

[2] str

The output value that appears in the "脚本内容" Html component.

### API name: /wrap_deep_podcast 包装函数，格式化脚本输出

```
copyfrom gradio_client import Client, handle_file

	client = Client("http://localhost:7861/")
	result = client.predict(
			topic="Hello!!",
			role_a_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			role_b_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			role_c_voice=handle_file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
			num_characters=2,
			depth_level="深度",
			api_name="/wrap_deep_podcast"
	)
	print(result)
```

#### Accepts 6 parameters:

------

topic str **Required**

The input value that is provided in the "播客主题（输入您想要讨论的主题）" Textbox component.

------

role_a_voice filepath **Required**

The input value that is provided in the "角色A音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

role_b_voice filepath **Required**

The input value that is provided in the "角色B音色（可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

role_c_voice filepath **Required**

The input value that is provided in the "角色C音色（可选，可上传或录制，点击麦克风图标可录制）" Audio component. The FileData class is a subclass of the GradioModel class that represents a file object within a Gradio interface. It is used to store file data and metadata when a file is uploaded. Attributes: path: The server file path where the file is stored. url: The normalized server URL pointing to the file. size: The size of the file in bytes. orig_name: The original filename before upload. mime_type: The MIME type of the file. is_stream: Indicates whether the file is a stream. meta: Additional metadata used internally (should not be changed).

------

num_characters float Default: 2

The input value that is provided in the "角色数量" Slider component.

------

depth_level Literal['深度', '中等', '浅层'] Default: "深度"

The input value that is provided in the "深度级别" Radio component.

#### Returns tuple of 3 elements

------

[0] filepath

The output value that appears in the "播客音频" Audio component.

------

[1] str

The output value that appears in the "状态信息" Textbox component.

------

[2] str

The output value that appears in the "脚本内容" Html component.