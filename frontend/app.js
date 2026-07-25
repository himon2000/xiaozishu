/**
 * 《小紫薯》App 入口
 * 负责：全局状态、登录态、角色切换、主题初始化
 *
 * 调用模式：wx.cloud.callContainer 内网调用（无需域名白名单）
 *
 * ⚙️  云托管配置：
 *   CLOUD_ENV_ID  →  腾讯云云开发环境ID
 *   SERVICE_NAME  →  云托管服务名称
 */

// ──────────────────────────────────────────────
// 🔧 云开发配置
// ⚠️ 发布前请替换为实际环境值
// ──────────────────────────────────────────────
// const CLOUD_ENV_ID = 'prod-9gkacmh0fb9cd5e6'; // 云开发环境ID（生产）
// const SERVICE_NAME = 'flask-4k93';   // 云托管服务名（生产）
// 统一使用同一套云环境（开发/体验/生产均对应同一个云环境）
// 如有独立开发环境可在此处区分
const { CLOUD_ENV_ID, SERVICE_NAME } = require('./config');
const { request } = require('./utils/request');
const { getStorageToken, setStorageToken, clearStorage } = require('./utils/auth');

App({
  globalData: {
    // 用户信息
    userInfo: null,
    token: null,

    // 云开发环境ID（供子模块使用）
    cloudEnvId: CLOUD_ENV_ID,
    serviceName: SERVICE_NAME,

    // 角色视图
    // 'seeker' 散修模式（买家视图）
    // 'provider' 大虾模式（卖家视图）
    viewMode: 'seeker',

    // 境界配置（从后端加载）
    levelConfig: [
      { level: 1, name: '炼气期', color: '#999999', icon: '🌫' },
      { level: 2, name: '筑基期', color: '#00cc44', icon: '🌿' },
      { level: 3, name: '金丹期', color: '#4499ff', icon: '💙' },
      { level: 4, name: '元婴期', color: '#cc44ff', icon: '💜' },
      { level: 5, name: '化神期', color: '#ffd700', icon: '⭐' },
    ],

    // 六大道法配置
    daoFaCategories: [],

    // 主题色
    theme: {
      primary: '#9b59b6',     // 紫色
      primaryLight: '#bb8fce', // 浅紫
      secondary: '#e8a0bf',   // 粉色
      background: '#faf7ff',  // 浅紫背景
      surface: '#ffffff',     // 白色卡片
      accent: '#f39c12',      // 橙色点缀
      text: '#2c2c2c',
      textSecondary: '#7f7f7f',
    },
  },

  onLaunch(options) {
    // 初始化云开发（必须在最早调用）
    wx.cloud.init({
      env: CLOUD_ENV_ID,
      traceUser: true,
    });

    // 检查登录态
    const token = getStorageToken();
    if (token) {
      this.globalData.token = token;
      this.refreshUserInfo();
    } else {
      // 无 token 时直接加载境界配置
      this.loadLevelConfig();
    }

    // 处理分享参数
    if (options.query && options.query.ref) {
      wx.setStorageSync('referral_code', options.query.ref);
    }
  },

  /**
   * 统一请求方法
   * 使用 wx.cloud.callContainer 内网调用（无需域名白名单）
   * 云托管网关自动注入 openid，无需 JWT
   */
  api(obj) {
    return request(obj);
  },

  request(obj) {
    return request(obj);
  },

  /**
   * 刷新用户信息
   */
  // ──────────────────────────────────────────────
  // 用户信息
  // ──────────────────────────────────────────────
  async refreshUserInfo() {
    try {
      const user = await this.api({ url: '/auth/me' });
      this.globalData.userInfo = user;
      this.globalData.viewMode = ['provider', 'elder', 'admin'].includes(user.role) ? 'provider' : 'seeker';
    } catch (e) {
      if (e.code === 401) {
        this.clearSession();
      }
    }
  },

  async loadLevelConfig() {
    try {
      const data = await this.api({ url: '/level/config' });
      if (data.levels) {
        this.globalData.levelConfig = data.levels;
      }
    } catch (e) {
      console.warn('加载境界配置失败:', e);
    }
  },

  // 切换角色视图
  switchViewMode(mode) {
    this.globalData.viewMode = mode;
    const pages = getCurrentPages();
    pages.forEach(page => {
      if (page.onViewModeSwitch) {
        page.onViewModeSwitch({ currentTarget: { dataset: { mode } } });
      }
    });
  },

  // 登录成功回调
  onLoginSuccess(token, userInfo) {
    setStorageToken(token);
    this.globalData.token = token;
    this.globalData.userInfo = userInfo;
    this.globalData.viewMode = ['provider', 'elder', 'admin'].includes(userInfo.role) ? 'provider' : 'seeker';
  },

  // 清除会话
  clearSession() {
    clearStorage();
    this.globalData.token = null;
    this.globalData.userInfo = null;
    this.globalData.viewMode = 'seeker';
  },

  // 获取境界信息
  getLevelInfo(level) {
    return this.globalData.levelConfig.find(l => l.level === level) || this.globalData.levelConfig[0];
  },

  // 统一错误处理
  handleError(err, customMsg) {
    console.error('[小紫薯 Error]', err);
    const msg = err.message || customMsg || '操作失败，请稍后重试';
    wx.showToast({ title: msg, icon: 'none', duration: 2000 });
  },
});
