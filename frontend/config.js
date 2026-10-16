// 云托管环境所属账号（资源提供方 AppID）
// 本小程序 wx776c4b107e04e36a 并非该云托管环境的开通方，是通过「资源复用」借用的。
// 前提：两个 AppID 必须同一主体，且已在资源方控制台完成资源复用授权。
const RESOURCE_APPID = 'wx616f58ee521ab283';
const CLOUD_ENV_ID = 'prod-8g726qeod6aba0bd';
const SERVICE_NAME = 'flask-qp8j';
const API_PREFIX = '/api/v1';
const TOKEN_KEY = 'access_token';
const LOCAL_API_BASE = 'http://127.0.0.1:8000';
// cloud：连接微信云托管；local：仅开发版连接本机 Docker 后端。
const API_MODE = 'cloud';
const FEATURES = Object.freeze({
  payment: false,
  dividend: false,
  researchTasks: false,
});

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
  RESOURCE_APPID,
  CLOUD_ENV_ID,
  SERVICE_NAME,
  API_PREFIX,
  TOKEN_KEY,
  API_MODE,
  LOCAL_API_BASE,
  FEATURES,
  USE_LOCAL_API: shouldUseLocalApi(),
};
