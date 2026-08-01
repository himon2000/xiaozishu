/**
 * 启动页 / 登录页
 * 路径：pages/splash/splash
 */
const app = getApp();
const { loginWithWechat, isLoggedIn } = require('../../utils/auth');
const { request } = require('../../utils/request');

Page({
  data: {
    logoUrl: '/assets/logo.png',
    slogan: '明明相代，代代相传',
    subSlogan: '校园接力 · 学长带飞 · 龙虾修仙',
    loading: false,
    showRoleSelect: false,
    cloudStatus: 'checking', // 'checking' | 'ok' | 'error'
    cloudError: '',
    agreed: false,
  },

  onLoad(options) {
    const agreed = wx.getStorageSync('privacy_agreed_v1') === true;
    this.setData({ agreed });
    // 处理飞花令牌
    if (options.ref) {
      wx.setStorageSync('referral_code', options.ref);
    }

    // 已登录 → 直接进入首页
    if (isLoggedIn() && agreed) {
      this.redirectToHome();
      return;
    }

    // 诊断云端连接状态
    this.checkCloudHealth();
  },

  async checkCloudHealth() {
    try {
      await request({ url: '/health', method: 'GET' });
      this.setData({ cloudStatus: 'ok' });
    } catch (e) {
      console.error('[splash] cloud health check fail:', e);
      let msg = '云端连接失败';
      if (e.errMsg && e.errMsg.includes('ERR_REQUEST')) {
        msg = '网络错误，请检查网络后重试';
      } else if (e.errMsg && e.errMsg.includes('Cloud')) {
        msg = '云开发未初始化，请检查 app.js';
      }
      this.setData({ cloudStatus: 'error', cloudError: msg });
    }
  },

  async onLoginTap() {
    if (this.data.loading) return;
    if (!this.data.agreed) {
      wx.showToast({ title: '请先阅读并同意协议', icon: 'none' });
      return;
    }
    this.setData({ loading: true });

    try {
      const result = await loginWithWechat();
      app.onLoginSuccess(result.access_token, result.user);

      // 新用户 → 显示角色选择
      if (result.user && result.user.is_new_user) {
        this.setData({ loading: false, showRoleSelect: true });
        return;
      }

      this.redirectToHome();
    } catch (e) {
      this.setData({ loading: false });
      console.error('[splash] login error:', e);
      wx.showModal({
        title: '登录失败',
        content: e.message || '请检查网络后重试',
        showCancel: false,
      });
    }
  },

  onAgreementChange(e) {
    const agreed = Array.isArray(e.detail.value) && e.detail.value.includes('agree');
    this.setData({ agreed });
    wx.setStorageSync('privacy_agreed_v1', agreed);
  },

  onOpenAgreement() {
    wx.navigateTo({ url: '/pages/legal/legal' });
  },

  onOpenPrivacy() {
    if (typeof wx.openPrivacyContract === 'function') {
      wx.openPrivacyContract({});
    }
  },

  onSelectRole(e) {
    const { role } = e.currentTarget.dataset;
    const userInfo = app.globalData.userInfo || {};
    userInfo.role = role;
    app.globalData.userInfo = userInfo;

    if (role === 'provider') {
      // profile 是 TabBar 页面，用 switchTab；通过 globalData 传 action
      app.globalData.profileAction = 'cert';
      wx.switchTab({ url: '/pages/profile/profile' });
    } else {
      this.redirectToHome();
    }
  },

  redirectToHome() {
    wx.switchTab({ url: '/pages/home/home' });
  },

  onShareAppMessage() {
    const referralCode = app.globalData.userInfo?.referral_code;
    return {
      title: '驯龙阁·明明相代校园接力平台',
      path: `/pages/splash/splash?ref=${referralCode || ''}`,
    };
  },
});
