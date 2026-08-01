/**
 * 我的角色 & 我的修为页面
 * 路径：subpackages/profile/growth-detail/growth-detail
 *
 * Tab: role（角色管理 + 添加人生阶段）/ growth（境界 + 成就 + 勋章）
 */
const { get, post } = require('../../../utils/request');

Page({
  data: {
    currentTab: 'role',
    user: null,
    currentRole: null,
    roles: [],

    // 境界配置
    allLevels: [
      { name: '炼气期', icon: '🌫' },
      { name: '筑基期', icon: '🌿' },
      { name: '金丹期', icon: '💙' },
      { name: '元婴期', icon: '💜' },
      { name: '化神期', icon: '⭐' },
    ],
    currentLevel: 1,
    levelConfig: { name: '炼气期', icon: '🌫' },
    nextLevelConfig: { name: '筑基期', icon: '🌿' },
    levelProgress: 0,

    // 成就列表
    achievements: [],

    // 勋章列表
    badges: [],

    // 角色列表（默认兜底）
    defaultRoles: [
      { role: 'seeker', name: '散修', icon: '🌱', desc: '浏览和发布需求', enabled: true },
      { role: 'provider', name: '大虾', icon: '📜', desc: '提供服务', enabled: false },
      { role: 'elder', name: '长老', icon: '🐲', desc: '传承与指导', enabled: false },
    ],
  },

  onLoad(options) {
    // 根据 profile 页传入的 tab 参数定位
    if (options.tab === 'growth') {
      this.setData({ currentTab: 'growth' });
    }
    this.loadData();
  },

  async loadData() {
    try {
      const userRes = await get('/auth/me').catch(() => null);
      const user = userRes || {};

      const roles = user.roles || [];
      const currentRole = user.current_role_obj || (roles.length > 0 ? roles.find(r => r.enabled) : null);
      const level = Math.max(1, Math.min(5, Number(user.level || 1)));
      const exp = Number(user.exp_points || 0);
      const thresholds = [0, 100, 500, 2000, 5000];
      const currentBase = thresholds[level - 1];
      const nextBase = thresholds[level] || currentBase;
      const levelProgress = level >= 5 ? 100 : Math.max(0, Math.min(100, ((exp - currentBase) / (nextBase - currentBase)) * 100));

      this.setData({
        user,
        currentRole,
        roles: roles.length > 0 ? roles : this.data.defaultRoles,
        currentLevel: level,
        levelConfig: this.data.allLevels[level - 1],
        nextLevelConfig: this.data.allLevels[Math.min(level, 4)],
        levelProgress: Math.round(levelProgress),
        achievements: [
          { id: 1, name: '初入江湖', icon: '🌱', desc: '完成首次注册', unlocked: true },
          { id: 2, name: '服务达人', icon: '📜', desc: '发布首个服务', unlocked: Number(user.total_services || 0) > 0 },
          { id: 3, name: '金丹修士', icon: '🔮', desc: '修为达到金丹期', unlocked: level >= 3 },
        ],
        badges: [
          { id: 1, name: '校园认证', icon: '🎓', desc: '完成校园信息认证', unlocked: Boolean(user.school) },
          { id: 2, name: '实名认证', icon: '✅', desc: '完成身份认证', unlocked: user.cert_status === 'verified' },
        ],
      });
    } catch (e) {
      console.error('加载角色数据失败', e);
    }
  },

  // ========== Tab 切换 ==========

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab });
  },

  // ========== 角色管理 ==========

  async onRoleTap(e) {
    const { role, enabled } = e.currentTarget.dataset;
    if (!enabled) {
      wx.showToast({ title: '角色未解锁', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '切换中...' });
    try {
      await post('/roles/switch', { role });
      const app = getApp();
      if (app.globalData.userInfo) app.globalData.userInfo.current_role = role;
      await this.loadData();
      wx.hideLoading();
      wx.showToast({ title: '角色切换成功', icon: 'success' });
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: error.message || '切换失败', icon: 'none' });
    }
  },

  onAddStage() {
    wx.navigateTo({ url: '/subpackages/profile/add-stage/add-stage' });
  },

  onShareAppMessage() {
    return {
      title: '查看我的成长轨迹，邀你一起修仙！',
      path: '/pages/home/home',
    };
  },
});
