/**
 * 认证工具
 * 使用 wx.cloud.callContainer 内网调用（无需域名白名单）
 */

const { TOKEN_KEY, USE_LOCAL_API } = require('../config');
const { request } = require('./request');

function getStorageToken() {
  return wx.getStorageSync(TOKEN_KEY);
}

function setStorageToken(token) {
  wx.setStorageSync(TOKEN_KEY, token);
}

function clearStorage() {
  wx.removeStorageSync(TOKEN_KEY);
}

function isLoggedIn() {
  return !!wx.getStorageSync(TOKEN_KEY);
}

/**
 * 认证请求同样遵循开发版走本机、正式版走云托管的规则。
 */
function cloudRequest(path, method, data, token) {
  return request({
    url: path,
    method: method || 'POST',
    data,
    header: token ? { 'Authorization': 'Bearer ' + token } : {},
  });
}

/**
 * 执行微信登录并获取 token
 */
function loginWithWechat() {
  if (USE_LOCAL_API) {
    return cloudRequest('/api/v1/auth/me', 'GET').then((user) => {
      const localToken = 'local-development-session';
      setStorageToken(localToken);
      return { access_token: localToken, user: { ...user, is_new_user: false } };
    });
  }
  return new Promise((resolve, reject) => {
    wx.login({
      success: async (res) => {
        if (!res.code) {
          return reject(new Error('wx.login 未返回 code'));
        }
        try {
          const data = await cloudRequest('/api/v1/auth/login', 'POST', { code: res.code });
          setStorageToken(data.access_token);
          resolve(data);
        } catch (e) {
          reject(e);
        }
      },
      fail: (err) => reject(err),
    });
  });
}

/**
 * 静默登录：检查 token 有效性
 */
async function ensureLogin() {
  const token = getStorageToken();
  if (!token) {
    return loginWithWechat();
  }
  try {
    const user = await cloudRequest('/api/v1/auth/me', 'GET', undefined, token);
    return { user, token };
  } catch (e) {
    if (e.code === 401) {
      return loginWithWechat();
    }
    throw e;
  }
}

module.exports = {
  getStorageToken,
  setStorageToken,
  clearStorage,
  isLoggedIn,
  loginWithWechat,
  ensureLogin,
};
