// pages/settings/settings.js - 我的设置
const app = getApp();
const { del } = require('../../utils/request');

Page({
  data: {
    notifyEnabled: true,
    soundEnabled: true,
    cacheSize: '计算中...',
    version: '1.0.0',
  },

  onLoad(options) {
    this.calcCacheSize();
    // 读取本地存储的用户偏好
    const settings = wx.getStorageSync('settings') || {};
    this.setData({
      notifyEnabled: settings.notifyEnabled !== false,
      soundEnabled: settings.soundEnabled !== false,
    });
  },

  // ========== 缓存计算 ==========

  calcCacheSize() {
    try {
      const res = wx.getStorageInfoSync();
      const sizeKB = res.currentSize || 0;
      let display = '';
      if (sizeKB < 1024) {
        display = sizeKB + ' KB';
      } else {
        display = (sizeKB / 1024).toFixed(1) + ' MB';
      }
      this.setData({ cacheSize: display });
    } catch (e) {
      this.setData({ cacheSize: '未知' });
    }
  },

  // ========== 开关操作 ==========

  onNotifyChange(e) {
    const enabled = e.detail.value;
    this.setData({ notifyEnabled: enabled });
    this.saveSettings({ notifyEnabled: enabled });
  },

  onSoundChange(e) {
    const enabled = e.detail.value;
    this.setData({ soundEnabled: enabled });
    this.saveSettings({ soundEnabled: enabled });
  },

  saveSettings(partial) {
    const settings = wx.getStorageSync('settings') || {};
    Object.assign(settings, partial);
    wx.setStorageSync('settings', settings);
  },

  // ========== 菜单跳转 ==========

  onPrivacy() {
    if (typeof wx.openPrivacyContract === 'function') {
      wx.openPrivacyContract({
        fail: () => wx.showToast({ title: '请先在公众平台完善隐私保护指引', icon: 'none' }),
      });
    }
  },

  onUserAgreement() {
    wx.navigateTo({ url: '/pages/legal/legal' });
  },

  onClearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '将清除本地缓存数据（不会影响账号信息），确认清除？',
      success: (res) => {
        if (res.confirm) {
          // 保留 settings 和 token
          const settings = wx.getStorageSync('settings');
          const token = wx.getStorageSync('access_token');
          wx.clearStorageSync();
          if (settings) wx.setStorageSync('settings', settings);
          if (token) wx.setStorageSync('access_token', token);
          this.calcCacheSize();
          wx.showToast({ title: '缓存已清除', icon: 'success' });
        }
      },
    });
  },

  onAbout() {
    wx.showModal({
      title: '关于小紫薯',
      content: '小紫薯 — 修仙风校园服务互助平台\n\n一款以修仙世界观为包装的校园互助服务小程序，连接师生需求，让校园生活更有趣。',
      showCancel: false,
      confirmText: '了解了',
    });
  },

  onCheckUpdate() {
    wx.showToast({ title: '已是最新版本', icon: 'none' });
  },

  onDeleteAccount() {
    wx.showModal({
      title: '注销账号',
      content: '注销后个人资料将被清除，且当前操作不可撤销。是否继续？',
      confirmText: '确认注销',
      confirmColor: '#d93025',
      success: async (result) => {
        if (!result.confirm) return;
        try {
          await del('/auth/me');
          app.clearSession();
          wx.reLaunch({ url: '/pages/splash/splash' });
        } catch (error) {
          wx.showToast({ title: error.message || '注销失败', icon: 'none' });
        }
      },
    });
    if (options && options.doc === 'agreement') {
      setTimeout(() => this.onUserAgreement(), 0);
    }
  },
});
