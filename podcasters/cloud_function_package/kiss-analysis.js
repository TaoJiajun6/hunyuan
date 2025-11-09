"use strict";

const axios = require('axios');

// 安全 stringify，避免循环引用
var stringifySafe = function (obj) {
  try {
    var cache = new Set();
    return JSON.stringify(obj, function (key, value) {
      if (typeof value === 'object' && value !== null) {
        if (cache.has(value)) return;
        cache.add(value);
      }
      return value;
    });
  } catch (e) {
    return JSON.stringify({ error: 'stringify error', message: String(e) });
  }
};

// 建议用环境变量存储API Key
const DASHSCOPE_API_KEY = process.env.DASHSCOPE_API_KEY || 'sk-xxx';

// 构建prompt
function buildPrompt(text) {
    return `
你是一个融合儒家智慧的自我成长助手。请根据用户提供的晨省、午省、暮省三个阶段的内容，按照三省-KISS整合模型生成每日成长总结。

### 输入数据结构：
${text}

### 输出要求：
1. 格式为JSON，字段包括：
   - keep（晨省规划的延续优势/午省所学的高效方法）
   - improve（午省发现的短板/暮省需升级的流程）
   - stop（暮省识别的低效行为/坏习惯）
   - start（晨省启用的新计划/暮省迭代的明日行动）
   - summary（三省智慧结晶，需引用《论语》金句点睛）

2. 内容绑定三省阶段：
   - keep = 晨省延续项 + 午省经验项
   - improve = 午省短板 + 暮省需升级项
   - stop = 暮省需戒除行为
   - start = 晨省新计划 + 暮省迭代行动

3. 权重分配：
   - 晨省建议占30%（启新程）
   - 午省建议占40%（关键调整期）
   - 暮省建议占30%（成果固化）

### 输出示例：
{
  "keep": "模块化开发方法，鸿蒙组件开发进度",
  "improve": "文档编写效率，承诺响应速度",
  "stop": "健身计划拖延",
  "start": "神经网络量化实践，承诺管理机制",
  "summary": "人而无信，不知其可也"
}

### 执行约束：
1. 输入数据必须包含三省结构：
   - 晨省-为人谋而不忠乎：当日目标规划（1-3条）
   - 午省-三人行必有我师：所学经验记录（1-2条）
   - 暮省-传不习乎：行为检验反思（1-3条）
2. 每条建议不超过8个汉字
3. 暮省反思优先覆盖晨省计划
4. summary必须引用《论语》金句点睛
`;
}

async function analyzeWithAI(text) {
  const prompt = buildPrompt(text);
  
  try {
    const response = await axios.post(
      'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
      {
        model: 'qwen-turbo',
        input: { prompt }
      },
      {
        headers: {
          'Authorization': `Bearer ${DASHSCOPE_API_KEY}`,
          'Content-Type': 'application/json'
        },
        timeout: 30000
      }
    );

    // 解析AI返回
    const outputText = response.data?.output?.text || '';
    const jsonStart = outputText.indexOf('{');
    const jsonEnd = outputText.lastIndexOf('}') + 1;
    
    let result = {
      keep: "",
      improve: "",
      stop: "",
      start: "",
      summary: "AI分析失败"
    };
    
    if (jsonStart !== -1 && jsonEnd !== -1) {
      try {
        result = JSON.parse(outputText.substring(jsonStart, jsonEnd));
      } catch (e) {
        console.error('JSON解析失败:', e);
      }
    }

    return { success: true, data: result };
  } catch (error) {
    console.error('AI分析请求失败:', error);
    return { 
      success: false, 
      error: error.message || 'AI分析失败'
    };
  }
}

// 统一风格的主处理函数
var myHandler = async function (event, context, callback) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  // 预检
  if (event && event.httpMethod === 'OPTIONS') {
    callback({
      statusCode: 204,
      headers: corsHeaders,
      body: ''
    });
    return;
  }

  try {
    // 解析输入参数
    let text = '';
    let body = event.body;
    
    if (body) {
      if (typeof body === 'string') {
        body = JSON.parse(body);
      }
      text = body.text || '';
    } else if (event.text) {
      text = event.text;
    }
    
    if (!text) {
      callback({
        statusCode: 400,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe({ 
          success: false, 
          message: 'text字段不能为空' 
        })
      });
      return;
    }

    console.log('开始调用AI分析接口...');
    const result = await analyzeWithAI(text);
    
    console.log('AI分析结果:', JSON.stringify(result));

    if (result.success) {
      callback({
        statusCode: 200,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe({
          success: true,
          data: result.data
        })
      });
    } else {
      callback({
        statusCode: 500,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe({ 
          success: false, 
          message: 'AI分析失败', 
          error: result.error 
        })
      });
    }
  } catch (error) {
    console.error('云函数执行错误:', error);
    callback({
      statusCode: 500,
      headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
      body: stringifySafe({ 
        success: false, 
        message: '三省KISS分析失败', 
        error: String(error) 
      })
    });
  }
};

exports.myHandler = myHandler;
