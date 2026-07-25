// pages/settings/settings.js - 我的设置
const app = getApp();

Page({
  data: {
    notifyEnabled: true,
    soundEnabled: true,
    cacheSize: '计算中...',
    version: '1.0.0',
  },

  onLoad() {
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
    wx.showModal({
      title: '隐私协议',
      content: '小紫薯重视用户隐私保护。我们仅收集必要信息以提供服务，不会将您的个人信息出售或共享给第三方。详情请关注后续更新。',
      showCancel: false,
      confirmText: '我知道了',
    });
  },

  onUserAgreement() {
    wx.showModal({
      title: '用户协议',
      content: '欢迎使用小紫薯校园服务互助平台。使用本服务即表示您同意遵守平台规则，尊重其他用户，合法合规使用平台功能。',
      showCancel: false,
      confirmText: '我知道了',
    });
  },

  onClearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '将清除本地缓存数据（不会影响账号信息），确认清除？',
      success: (res) => {
        if (res.confirm) {
          // 保留 settings 和 token
          const settings = wx.getStorageSync('settings');
          const token = wx.getStorageSync('token');
          wx.clearStorageSync();
          if (settings) wx.setStorageSync('settings', settings);
          if (token) wx.setStorageSync('token', token);
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
});
