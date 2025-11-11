"use strict";

const axios = require('axios');
const https = require('https');

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
// 支持 Cloud Studio 端口转发地址格式：https://${SPACE_KEY}--${PORT}.${REGION}.cloudstudio.work
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'https://pexlsj--8000.ap-singapore.cloudstudio.work';
const API_TIMEOUT = 600000; // 10分钟超时（考虑大文件上传和播客生成时间）

/**
 * 转发请求到后端API服务器
 */
async function forwardToBackend(endpoint, requestData) {
  try {
    // 确保URL格式正确（移除末尾斜杠，添加路径）
    const baseUrl = BACKEND_API_URL.replace(/\/+$/, '');
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${cleanEndpoint}`;
    
    console.log(`转发请求到: ${url}`);
    console.log(`请求数据大小: ${JSON.stringify(requestData).length} bytes`);
    // 记录角色信息，但不记录完整的base64数据（避免日志过大）
    if (requestData.role_voices) {
      console.log(`角色数量: ${Object.keys(requestData.role_voices).length}, 角色名称: ${Object.keys(requestData.role_voices).join(', ')}`);
    }
    if (requestData.characters) {
      console.log(`角色数量: ${requestData.characters.length}, 角色名称: ${requestData.characters.map(c => c.name).join(', ')}`);
    }
    
    const response = await axios.post(url, requestData, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: API_TIMEOUT,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
      // 对于HTTPS，确保不验证证书（如果Cloud Studio使用自签名证书）
      httpsAgent: process.env.SKIP_SSL_VERIFY === 'true' ? 
        new https.Agent({ rejectUnauthorized: false }) : undefined
    });

    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    console.error('后端API请求失败:', error.message);
    if (error.code === 'ECONNABORTED') {
      console.error('请求超时');
      return {
        success: false,
        error: `请求超时（${API_TIMEOUT / 1000}秒），播客生成可能需要更长时间，请稍后重试`,
        statusCode: 504
      };
    } else if (error.response) {
      console.error('响应状态:', error.response.status);
      console.error('响应数据:', error.response.data);
      // 处理后端返回的错误响应
      const errorData = error.response.data;
      if (errorData && typeof errorData === 'object') {
        return {
          success: false,
          error: errorData.error || errorData.message || error.message,
          statusCode: error.response.status,
          data: errorData
        };
      } else {
        return {
          success: false,
          error: errorData || error.message || `HTTP ${error.response.status}`,
          statusCode: error.response.status
        };
      }
    } else if (error.request) {
      console.error('请求发送失败，未收到响应');
      return {
        success: false,
        error: '无法连接到后端服务器，请检查服务器地址和网络连接',
        statusCode: 503
      };
    } else {
      console.error('请求配置错误:', error.message);
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
    // 确保URL格式正确
    const baseUrl = BACKEND_API_URL.replace(/\/+$/, '');
    const url = `${baseUrl}/health`;
    console.log(`健康检查请求: ${url}`);
    
    const response = await axios.get(url, {
      timeout: 10000,
      headers: {
        'Accept': 'application/json'
      },
      // 对于HTTPS，确保不验证证书（如果Cloud Studio使用自签名证书）
      httpsAgent: process.env.SKIP_SSL_VERIFY === 'true' ? 
        new https.Agent({ rejectUnauthorized: false }) : undefined
    });
    return {
      success: true,
      data: response.data
    };
  } catch (error) {
    console.error('健康检查失败:', error.message);
    if (error.response) {
      return {
        success: false,
        error: `健康检查失败: HTTP ${error.response.status} - ${error.response.statusText}`
      };
    } else if (error.request) {
      return {
        success: false,
        error: '无法连接到后端服务器，请检查服务器地址和网络连接'
      };
    } else {
      return {
        success: false,
        error: error.message || '健康检查失败'
      };
    }
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
    if (httpMethod === 'GET' && (path === '/health' || path === 'health' || queryParams.path === 'health' || !path || path === '/')) {
      const result = await healthCheck();
      callback({
        statusCode: result.success ? 200 : 503,
        headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders),
        body: stringifySafe(result.success ? {
          success: true,
          data: result.data
        } : {
          success: false,
          message: '健康检查失败',
          error: result.error
        })
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

