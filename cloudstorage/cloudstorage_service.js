/**
 * 华为AGC云存储服务 - Node.js Server SDK实现
 * 用于上传和下载音色文件、播客文件等
 */

const {AGCClient, CredentialParser} = require('@agconnect/common-server');
const {StorageManagement} = require('@agconnect/cloudstorage-server');
const fs = require('fs');
const path = require('path');

// 配置凭据文件路径（可以通过环境变量或参数传入）
const CREDENTIAL_PATH = process.env.AGC_CONFIG || path.join(__dirname, '../hunyuan_podcast/agc-apiclient-*.json');
const BUCKET_NAME = process.env.AGC_BUCKET || 'podcasters-y0qig';

// 初始化AGC客户端
let storageInitialized = false;

function initializeStorage(credentialPath = null) {
  if (storageInitialized) {
    return;
  }
  
  try {
    // 如果提供了凭据路径，使用提供的路径；否则尝试从环境变量或默认路径获取
    let actualCredentialPath = credentialPath;
    
    if (!actualCredentialPath) {
      // 尝试从环境变量获取
      if (process.env.AGC_CONFIG) {
        actualCredentialPath = process.env.AGC_CONFIG;
      } else {
        // 尝试查找默认位置的凭据文件
        try {
          const glob = require('glob');
          const matches = glob.sync(path.join(__dirname, '../hunyuan_podcast/agc-apiclient-*.json'));
          if (matches.length > 0) {
            actualCredentialPath = matches[0];
          } else {
            throw new Error('未找到AGC凭据文件，请设置AGC_CONFIG环境变量或提供credentialPath参数');
          }
        } catch (globError) {
          // 如果glob模块不可用，尝试使用fs模块查找
          const fs = require('fs');
          const hunyuanDir = path.join(__dirname, '../hunyuan_podcast');
          if (fs.existsSync(hunyuanDir)) {
            const files = fs.readdirSync(hunyuanDir);
            const credentialFile = files.find(f => f.startsWith('agc-apiclient-') && f.endsWith('.json'));
            if (credentialFile) {
              actualCredentialPath = path.join(hunyuanDir, credentialFile);
            } else {
              throw new Error('未找到AGC凭据文件，请设置AGC_CONFIG环境变量或提供credentialPath参数');
            }
          } else {
            throw new Error('未找到AGC凭据文件，请设置AGC_CONFIG环境变量或提供credentialPath参数');
          }
        }
      }
    }
    
    const credential = CredentialParser.toCredential(actualCredentialPath);
    AGCClient.initialize(credential);
    storageInitialized = true;
    console.log(`AGC客户端初始化成功，使用凭据文件: ${actualCredentialPath}`);
  } catch (error) {
    console.error('AGC客户端初始化失败:', error);
    throw error;
  }
}

/**
 * 上传文件到云存储
 * @param {string} localFilePath - 本地文件路径
 * @param {string} cloudPath - 云存储路径（如 'outputs/podcasts/podcast.wav' 或 'voices/voice1.wav'）
 * @param {string} bucketName - 存储桶名称（可选，默认使用BUCKET_NAME）
 * @returns {Promise<Object>} 上传结果，包含文件URL等信息
 */
async function uploadFile(localFilePath, cloudPath, bucketName = BUCKET_NAME) {
  try {
    // 确保已初始化
    if (!storageInitialized) {
      initializeStorage();
    }
    
    // 检查本地文件是否存在
    if (!fs.existsSync(localFilePath)) {
      throw new Error(`本地文件不存在: ${localFilePath}`);
    }
    
    const storage = new StorageManagement();
    const bucket = storage.bucket(bucketName);
    
    console.log(`开始上传文件: ${localFilePath} -> ${cloudPath}`);
    
    // 上传文件
    const result = await bucket.upload(localFilePath, {
      destination: cloudPath,
      metadata: {
        contentType: getContentType(localFilePath),
        customMetadata: {
          uploadTime: new Date().toISOString(),
          fileName: path.basename(localFilePath)
        }
      }
    });
    
    console.log(`文件上传成功: ${cloudPath}`);
    return {
      success: true,
      cloudPath: cloudPath,
      url: result.selfLink || `https://ops-server-drcn.agcstorage.link/v0/${bucketName}/${cloudPath}`,
      metadata: result
    };
  } catch (error) {
    console.error(`文件上传失败: ${error.message}`, error);
    throw error;
  }
}

/**
 * 从云存储下载文件
 * @param {string} cloudPath - 云存储路径
 * @param {string} localFilePath - 本地保存路径
 * @param {string} bucketName - 存储桶名称（可选，默认使用BUCKET_NAME）
 * @returns {Promise<Object>} 下载结果
 */
async function downloadFile(cloudPath, localFilePath, bucketName = BUCKET_NAME) {
  try {
    // 确保已初始化
    if (!storageInitialized) {
      initializeStorage();
    }
    
    const storage = new StorageManagement();
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(cloudPath);
    
    // 确保本地目录存在
    const localDir = path.dirname(localFilePath);
    if (!fs.existsSync(localDir)) {
      fs.mkdirSync(localDir, { recursive: true });
    }
    
    console.log(`开始下载文件: ${cloudPath} -> ${localFilePath}`);
    
    // 创建写入流
    const writeStream = fs.createWriteStream(localFilePath);
    
    // 下载文件
    return new Promise((resolve, reject) => {
      file.createReadStream()
        .on('error', (error) => {
          console.error(`文件下载失败: ${error.message}`, error);
          reject(error);
        })
        .on('end', () => {
          console.log(`文件下载成功: ${localFilePath}`);
          resolve({
            success: true,
            localPath: localFilePath,
            cloudPath: cloudPath
          });
        })
        .pipe(writeStream);
    });
  } catch (error) {
    console.error(`文件下载失败: ${error.message}`, error);
    throw error;
  }
}

/**
 * 上传播客文件
 * @param {string} podcastFilePath - 播客文件本地路径
 * @param {string} fileName - 文件名（可选，默认使用原文件名）
 * @returns {Promise<Object>} 上传结果
 */
async function uploadPodcast(podcastFilePath, fileName = null) {
  const actualFileName = fileName || path.basename(podcastFilePath);
  const cloudPath = `outputs/podcasts/${actualFileName}`;
  return await uploadFile(podcastFilePath, cloudPath);
}

/**
 * 上传音色文件
 * @param {string} voiceFilePath - 音色文件本地路径
 * @param {string} fileName - 文件名（可选，默认使用原文件名）
 * @returns {Promise<Object>} 上传结果
 */
async function uploadVoice(voiceFilePath, fileName = null) {
  const actualFileName = fileName || path.basename(voiceFilePath);
  const cloudPath = `voices/${actualFileName}`;
  return await uploadFile(voiceFilePath, cloudPath);
}

/**
 * 下载播客文件
 * @param {string} cloudPath - 云存储路径（如 'outputs/podcasts/podcast.wav'）
 * @param {string} localDir - 本地保存目录（可选，默认使用当前目录的downloads文件夹）
 * @returns {Promise<Object>} 下载结果
 */
async function downloadPodcast(cloudPath, localDir = null) {
  const fileName = path.basename(cloudPath);
  const actualLocalDir = localDir || path.join(__dirname, '../downloads/podcasts');
  const localFilePath = path.join(actualLocalDir, fileName);
  return await downloadFile(cloudPath, localFilePath);
}

/**
 * 下载音色文件
 * @param {string} cloudPath - 云存储路径（如 'voices/voice1.wav'）
 * @param {string} localDir - 本地保存目录（可选，默认使用当前目录的downloads文件夹）
 * @returns {Promise<Object>} 下载结果
 */
async function downloadVoice(cloudPath, localDir = null) {
  const fileName = path.basename(cloudPath);
  const actualLocalDir = localDir || path.join(__dirname, '../downloads/voices');
  const localFilePath = path.join(actualLocalDir, fileName);
  return await downloadFile(cloudPath, localFilePath);
}

/**
 * 获取文件元数据
 * @param {string} cloudPath - 云存储路径
 * @param {string} bucketName - 存储桶名称（可选）
 * @returns {Promise<Object>} 文件元数据
 */
async function getFileMetadata(cloudPath, bucketName = BUCKET_NAME) {
  try {
    if (!storageInitialized) {
      initializeStorage();
    }
    
    const storage = new StorageManagement();
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(cloudPath);
    
    const metadata = await file.getMetadata();
    return {
      success: true,
      metadata: metadata
    };
  } catch (error) {
    console.error(`获取文件元数据失败: ${error.message}`, error);
    throw error;
  }
}

/**
 * 列出文件
 * @param {string} prefix - 路径前缀（可选，如 'outputs/podcasts/'）
 * @param {string} bucketName - 存储桶名称（可选）
 * @returns {Promise<Array>} 文件列表
 */
async function listFiles(prefix = '', bucketName = BUCKET_NAME) {
  try {
    if (!storageInitialized) {
      initializeStorage();
    }
    
    const storage = new StorageManagement();
    const bucket = storage.bucket(bucketName);
    
    const result = await bucket.getFiles({ prefix: prefix, delimiter: '/' });
    return {
      success: true,
      files: result[0] || [],
      prefixes: result[1] || []
    };
  } catch (error) {
    console.error(`列出文件失败: ${error.message}`, error);
    throw error;
  }
}

/**
 * 删除文件
 * @param {string} cloudPath - 云存储路径
 * @param {string} bucketName - 存储桶名称（可选）
 * @returns {Promise<Object>} 删除结果
 */
async function deleteFile(cloudPath, bucketName = BUCKET_NAME) {
  try {
    if (!storageInitialized) {
      initializeStorage();
    }
    
    const storage = new StorageManagement();
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(cloudPath);
    
    await file.delete();
    return {
      success: true,
      cloudPath: cloudPath
    };
  } catch (error) {
    console.error(`删除文件失败: ${error.message}`, error);
    throw error;
  }
}

/**
 * 根据文件扩展名获取Content-Type
 */
function getContentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentTypes = {
    '.wav': 'audio/x-wav',
    '.mp3': 'audio/mpeg',
    '.m4a': 'audio/mp4',
    '.flac': 'audio/flac',
    '.ogg': 'audio/ogg',
    '.txt': 'text/plain',
    '.json': 'application/json'
  };
  return contentTypes[ext] || 'application/octet-stream';
}

// 如果直接运行此文件，提供命令行接口
if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0];
  
  async function main() {
    try {
      initializeStorage();
      
      switch (command) {
        case 'upload':
          if (args.length < 3) {
            console.error('用法: node cloudstorage_service.js upload <本地文件路径> <云存储路径>');
            process.exit(1);
          }
          const result = await uploadFile(args[1], args[2]);
          console.log('上传成功:', JSON.stringify(result, null, 2));
          break;
          
        case 'download':
          if (args.length < 3) {
            console.error('用法: node cloudstorage_service.js download <云存储路径> <本地文件路径>');
            process.exit(1);
          }
          const downloadResult = await downloadFile(args[1], args[2]);
          console.log('下载成功:', JSON.stringify(downloadResult, null, 2));
          break;
          
        case 'list':
          const prefix = args[1] || '';
          const listResult = await listFiles(prefix);
          console.log('文件列表:', JSON.stringify(listResult, null, 2));
          break;
          
        case 'delete':
          if (args.length < 2) {
            console.error('用法: node cloudstorage_service.js delete <云存储路径>');
            process.exit(1);
          }
          const deleteResult = await deleteFile(args[1]);
          console.log('删除成功:', JSON.stringify(deleteResult, null, 2));
          break;
          
        default:
          console.log(`
用法:
  node cloudstorage_service.js <command> [args...]

命令:
  upload <本地文件路径> <云存储路径>    - 上传文件
  download <云存储路径> <本地文件路径>  - 下载文件
  list [前缀]                          - 列出文件
  delete <云存储路径>                   - 删除文件

示例:
  node cloudstorage_service.js upload ./podcast.wav outputs/podcasts/podcast.wav
  node cloudstorage_service.js download outputs/podcasts/podcast.wav ./downloads/podcast.wav
  node cloudstorage_service.js list outputs/podcasts/
          `);
      }
    } catch (error) {
      console.error('错误:', error);
      process.exit(1);
    }
  }
  
  main();
}

// 导出函数供其他模块使用
module.exports = {
  initializeStorage,
  uploadFile,
  downloadFile,
  uploadPodcast,
  uploadVoice,
  downloadPodcast,
  downloadVoice,
  getFileMetadata,
  listFiles,
  deleteFile
};

