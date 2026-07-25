/**
 * 统一 HTTP 请求封装
 * 使用 wx.cloud.callContainer 内网调用（无需域名白名单）
 *
 * 优先级：
 *   1. wx.cloud.callContainer（内网，自动注入 openid，无需域名白名单）
 *   2. 如果 cloud 不可用则报错提示
 */

// 云托管配置（与 app.js 保持一致）
const {
  CLOUD_ENV_ID,
  SERVICE_NAME,
  API_PREFIX,
  TOKEN_KEY,
  LOCAL_API_BASE,
  USE_LOCAL_API,
} = require('../config');

function buildQuery(params = {}) {
  return Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
}

function request(options) {
  const { url, method = 'GET', data, header = {} } = options;
  const upperMethod = method.toUpperCase();

  // 安全获取 token（在函数内部延迟获取，避免初始化时序问题）
  const app = getApp();
  const token = wx.getStorageSync(TOKEN_KEY) ||
    (app && app.globalData && app.globalData.token) || '';

  let path = (url === '/health' || url.startsWith('/api')) ? url : (API_PREFIX + url);
  const query = upperMethod === 'GET' && data && typeof data === 'object' ? buildQuery(data) : '';
  if (query) {
    path += (path.includes('?') ? '&' : '?') + query;
  }

  return new Promise((resolve, reject) => {
    const success = (res) => {
      if (res.statusCode === 401) {
        // Token 失效，触发重新登录
        if (app) app.clearSession();
        wx.showToast({ title: '请重新登录', icon: 'none' });
        wx.reLaunch({ url: '/pages/splash/splash' });
        return reject({ code: 401, message: '请重新登录', detail: '请重新登录' });
      }
      if (res.statusCode >= 200 && res.statusCode < 300) {
        const payload = res.data;
        if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'code')) {
          if (payload.code !== 0) {
            const message = payload.message || payload.msg || '请求失败';
            reject({ code: payload.code, message, detail: message });
            return;
          }
          if (Object.prototype.hasOwnProperty.call(payload, 'data')) {
            resolve(payload.data);
            return;
          }
        }
        resolve(payload);
      } else {
        const message = (res.data && (res.data.detail || res.data.message)) || '请求失败';
        reject({ code: res.statusCode, message, detail: message });
      }
    };
    const fail = (err) => {
      console.error('[request] request fail:', path, err);
      reject({ code: -1, message: '网络请求失败，请检查网络', detail: '网络请求失败，请检查网络' });
    };
    const commonHeaders = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': 'Bearer ' + token } : {}),
      ...header,
    };

    if (USE_LOCAL_API) {
      wx.request({
        url: LOCAL_API_BASE + path,
        method: upperMethod,
        header: {
          ...commonHeaders,
          // 本地没有微信网关注入 openid，固定开发身份保证读写同一条用户记录。
          'X-WX-OPENID': wx.getStorageSync('dev_openid') || 'local-dev-user',
        },
        data: upperMethod === 'GET' ? undefined : data,
        success,
        fail,
      });
      return;
    }

    wx.cloud.callContainer({
      config: { env: CLOUD_ENV_ID },
      path,
      method: upperMethod,
      header: {
        ...commonHeaders,
        'X-WX-SERVICE': SERVICE_NAME,
      },
      data: upperMethod === 'GET' ? undefined : data,
      success,
      fail,
    });
  });
}

// 便捷方法
const get = (url, params) => request({ url, data: params });
const post = (url, data) => request({ url, method: 'POST', data });
const put = (url, data) => request({ url, method: 'PUT', data });
const patch = (url, data) => request({ url, method: 'PATCH', data });
const del = (url) => request({ url, method: 'DELETE' });

module.exports = { request, get, post, put, patch, del };
