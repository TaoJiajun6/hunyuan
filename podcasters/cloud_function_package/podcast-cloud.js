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

// 后端API服务器地址（从环境变量读取，如果没有则使用默认值）
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://10.10.210.52:8000';
const API_TIMEOUT = 300000; // 5分钟超时（播客生成可能需要较长时间）

/**
 * 转发请求到后端API服务器
 */
async function forwardToBackend(endpoint, requestData) {
  try {
    const url = `${BACKEND_API_URL}${endpoint}`;
    console.log(`转发请求到: ${url}`);
    console.log(`请求数据: ${JSON.stringify({ ...requestData, role_voices: Object.keys(requestData.role_voices || {}) })}`);
    
    const response = await axios.post(url, requestData, {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: API_TIMEOUT,
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    });

    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    console.error('后端API请求失败:', error.message);
    if (error.response) {
      console.error('响应状态:', error.response.status);
      console.error('响应数据:', error.response.data);
      return {
        success: false,
        error: error.response.data?.error || error.response.data?.message || error.message,
        statusCode: error.response.status
      };
    } else if (error.request) {
      return {
        success: false,
        error: '无法连接到后端服务器，请检查服务器是否正常运行',
        statusCode: 503
      };
    } else {
      return {
        success: false,
        error: error.message || '请求失败',
        statusCode: 500
      };
    }
  }
}

/**
 * 健康检查
 */
async function healthCheck() {
  try {
    const url = `${BACKEND_API_URL}/health`;
    const response = await axios.get(url, {
      timeout: 10000
    });
    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    return {
      success: false,
      error: error.message || '健康检查失败'
    };
  }
}

/**
 * 云函数主处理函数
 */
var myHandler = async function (event, context, callback) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };

  // 预检请求
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
    const httpMethod = event.httpMethod || event.requestContext?.http?.method || 'POST';
    let body = event.body;
    let path = event.path || event.pathParameters?.path || event.rawPath || '';
    let queryParams = event.queryStringParameters || event.queryParameters || {};
    
    // 如果是GET请求且路径为/health，执行健康检查
    if (httpMethod === 'GET' && (path === '/health' || path === 'health' || queryParams.path === 'health' || !path)) {
      const result = await healthCheck();
      callback({
        statusCode: result.success ? 200 : 503,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe(result)
      });
      return;
    }
    
    // 解析请求体
    if (body) {
      if (typeof body === 'string') {
        try {
          body = JSON.parse(body);
        } catch (e) {
          // 如果解析失败，保持原样
        }
      }
    } else {
      body = event;
    }

    // 根据请求类型分发
    let endpoint = '';
    let requestData = body;

    // 根据路径或请求体判断请求类型
    // 优先级：路径 > 请求体内容
    if (path.includes('multi_role') || queryParams.type === 'multi_role') {
      // 多角色互动播客
      endpoint = '/api/v1/podcast/multi_role';
      requestData = {
        text: body.text || '',
        role_voices: body.role_voices || {},
        silence_interval: body.silence_interval || 300
      };
    } else if (path.includes('character') || queryParams.type === 'character') {
      // 自定义角色播客
      endpoint = '/api/v1/podcast/character';
      requestData = {
        characters: body.characters || [],
        topic: body.topic || undefined,
        silence_interval: body.silence_interval || 300
      };
    } else if (path.includes('deep') || queryParams.type === 'deep') {
      // 主题深度播客
      endpoint = '/api/v1/podcast/deep';
      requestData = {
        topic: body.topic || '',
        role_voices: body.role_voices || {},
        num_characters: body.num_characters || 2,
        depth_level: body.depth_level || '深度',
        silence_interval: body.silence_interval || 300
      };
    } else if (body.text !== undefined && body.role_voices !== undefined && !body.characters) {
      // 根据请求体判断：多角色互动播客
      endpoint = '/api/v1/podcast/multi_role';
      requestData = {
        text: body.text || '',
        role_voices: body.role_voices || {},
        silence_interval: body.silence_interval || 300
      };
    } else if (body.characters !== undefined && Array.isArray(body.characters)) {
      // 根据请求体判断：自定义角色播客
      endpoint = '/api/v1/podcast/character';
      requestData = {
        characters: body.characters || [],
        topic: body.topic || undefined,
        silence_interval: body.silence_interval || 300
      };
    } else if (body.topic !== undefined && body.role_voices !== undefined && !body.text) {
      // 根据请求体判断：主题深度播客
      endpoint = '/api/v1/podcast/deep';
      requestData = {
        topic: body.topic || '',
        role_voices: body.role_voices || {},
        num_characters: body.num_characters || 2,
        depth_level: body.depth_level || '深度',
        silence_interval: body.silence_interval || 300
      };
    } else {
      // 未知请求类型
      callback({
        statusCode: 400,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe({
          success: false,
          message: '未知的请求类型，请检查请求参数或路径',
          error: 'Invalid request type',
          hint: '请确保请求体包含正确的字段，或使用查询参数 type=multi_role|character|deep'
        })
      });
      return;
    }

    // 验证必要参数
    if (endpoint === '/api/v1/podcast/multi_role') {
      if (!requestData.text || !requestData.role_voices || Object.keys(requestData.role_voices).length === 0) {
        callback({
          statusCode: 400,
          headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
          body: stringifySafe({
            success: false,
            message: '多角色播客请求缺少必要参数：text 和 role_voices',
            error: 'Missing required parameters'
          })
        });
        return;
      }
    } else if (endpoint === '/api/v1/podcast/character') {
      if (!requestData.characters || requestData.characters.length < 2) {
        callback({
          statusCode: 400,
          headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
          body: stringifySafe({
            success: false,
            message: '自定义角色播客请求需要至少2个角色',
            error: 'Missing required parameters'
          })
        });
        return;
      }
    } else if (endpoint === '/api/v1/podcast/deep') {
      if (!requestData.topic || !requestData.role_voices || Object.keys(requestData.role_voices).length === 0) {
        callback({
          statusCode: 400,
          headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
          body: stringifySafe({
            success: false,
            message: '主题深度播客请求缺少必要参数：topic 和 role_voices',
            error: 'Missing required parameters'
          })
        });
        return;
      }
    }

    console.log(`开始处理请求: ${endpoint}`);
    const result = await forwardToBackend(endpoint, requestData);

    if (result.success) {
      // 如果后端返回的数据格式是 { success, message, data }，直接使用
      // 否则包装为标准格式
      let responseData = result.data;
      if (responseData && responseData.success !== undefined) {
        callback({
          statusCode: 200,
          headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
          body: stringifySafe(responseData)
        });
      } else {
        callback({
          statusCode: 200,
          headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
          body: stringifySafe({
            success: true,
            message: '播客生成成功',
            data: responseData
          })
        });
      }
    } else {
      callback({
        statusCode: result.statusCode || 500,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe({
          success: false,
          message: '播客生成失败',
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
        message: '播客生成失败',
        error: String(error)
      })
    });
  }
};

exports.myHandler = myHandler;

