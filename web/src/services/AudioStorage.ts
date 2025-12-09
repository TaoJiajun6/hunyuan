/**
 * 音频存储服务
 * 使用 IndexedDB 存储大型音频数据（支持几百MB到几GB）
 */

const DB_NAME = 'PodcastAudioDB';
const DB_VERSION = 1;
const STORE_NAME = 'audioData';

interface AudioRecord {
  id: string;
  audioBase64: string;
  timestamp: number;
}

let db: IDBDatabase | null = null;

/**
 * 初始化 IndexedDB
 */
function initDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (db) {
      resolve(db);
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      reject(new Error('无法打开 IndexedDB'));
    };

    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = (event.target as IDBOpenDBRequest).result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        const objectStore = database.createObjectStore(STORE_NAME, { keyPath: 'id' });
        objectStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

/**
 * 保存音频数据到 IndexedDB
 */
export async function saveAudioToIndexedDB(podcastId: string, audioBase64: string): Promise<void> {
  try {
    const database = await initDB();
    const transaction = database.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    const record: AudioRecord = {
      id: podcastId,
      audioBase64: audioBase64,
      timestamp: Date.now(),
    };

    return new Promise((resolve, reject) => {
      const request = store.put(record);
      request.onsuccess = () => {
        console.log('音频数据已保存到 IndexedDB，播客ID:', podcastId);
        resolve();
      };
      request.onerror = () => {
        reject(new Error('保存音频数据失败'));
      };
    });
  } catch (error) {
    console.error('保存音频到 IndexedDB 失败:', error);
    throw error;
  }
}

/**
 * 从 IndexedDB 获取音频数据
 */
export async function getAudioFromIndexedDB(podcastId: string): Promise<string | null> {
  try {
    const database = await initDB();
    const transaction = database.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);

    return new Promise((resolve, reject) => {
      const request = store.get(podcastId);
      request.onsuccess = () => {
        const result = request.result;
        if (result) {
          resolve(result.audioBase64);
        } else {
          resolve(null);
        }
      };
      request.onerror = () => {
        reject(new Error('获取音频数据失败'));
      };
    });
  } catch (error) {
    console.error('从 IndexedDB 获取音频失败:', error);
    return null;
  }
}

/**
 * 从 IndexedDB 删除音频数据
 */
export async function deleteAudioFromIndexedDB(podcastId: string): Promise<void> {
  try {
    const database = await initDB();
    const transaction = database.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);

    return new Promise((resolve, reject) => {
      const request = store.delete(podcastId);
      request.onsuccess = () => {
        console.log('音频数据已从 IndexedDB 删除，播客ID:', podcastId);
        resolve();
      };
      request.onerror = () => {
        reject(new Error('删除音频数据失败'));
      };
    });
  } catch (error) {
    console.error('从 IndexedDB 删除音频失败:', error);
    throw error;
  }
}

/**
 * 清理旧的音频数据（保留最近N个）
 */
export async function cleanOldAudioData(keepCount: number = 50): Promise<void> {
  try {
    const database = await initDB();
    const transaction = database.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index('timestamp');

    return new Promise((resolve, reject) => {
      const request = index.openCursor(null, 'prev'); // 从新到旧
      const records: AudioRecord[] = [];
      
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
        if (cursor) {
          records.push(cursor.value);
          cursor.continue();
        } else {
          // 删除超出保留数量的记录
          const toDelete = records.slice(keepCount);
          let deleteCount = 0;
          
          if (toDelete.length === 0) {
            resolve();
            return;
          }
          
          toDelete.forEach((record) => {
            const deleteRequest = store.delete(record.id);
            deleteRequest.onsuccess = () => {
              deleteCount++;
              if (deleteCount === toDelete.length) {
                console.log(`已清理 ${deleteCount} 个旧音频数据`);
                resolve();
              }
            };
            deleteRequest.onerror = () => {
              reject(new Error('清理旧数据失败'));
            };
          });
        }
      };
      
      request.onerror = () => {
        reject(new Error('查询音频数据失败'));
      };
    });
  } catch (error) {
    console.error('清理旧音频数据失败:', error);
    throw error;
  }
}

