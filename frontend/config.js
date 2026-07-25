const CLOUD_ENV_ID = 'prod-9gkacmh0fb9cd5e6';
const SERVICE_NAME = 'flask-4k93';
const API_PREFIX = '/api/v1';
const TOKEN_KEY = 'access_token';
const LOCAL_API_BASE = 'http://127.0.0.1:8000';
// cloud：连接微信云托管；local：仅开发版连接本机 Docker 后端。
const API_MODE = 'cloud';

// 只有显式切换为 local 时，微信开发者工具才读取本机 MySQL。
function shouldUseLocalApi() {
  try {
    return API_MODE === 'local'
      && wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
  } catch (e) {
    return false;
  }
}

module.exports = {
  CLOUD_ENV_ID,
  SERVICE_NAME,
  API_PREFIX,
  TOKEN_KEY,
  API_MODE,
  LOCAL_API_BASE,
  USE_LOCAL_API: shouldUseLocalApi(),
};
