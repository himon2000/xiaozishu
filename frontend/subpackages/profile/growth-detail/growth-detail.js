/**
 * 我的角色 & 我的修为页面
 * 路径：subpackages/profile/growth-detail/growth-detail
 *
 * Tab: role（角色管理 + 添加人生阶段）/ growth（境界 + 成就 + 勋章）
 */
const { get } = require('../../../utils/request');

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
    levelProgress: 60,

    // 成就列表
    achievements: [
      { id: 1, name: '初入江湖', icon: '🌱', desc: '完成首次注册', unlocked: true },
      { id: 2, name: '服务达人', icon: '📜', desc: '发布首个服务', unlocked: true },
      { id: 3, name: '需求发起者', icon: '📋', desc: '发布首个需求', unlocked: true },
      { id: 4, name: '飞花使者', icon: '🎫', desc: '邀请10位道友', unlocked: false },
      { id: 5, name: '金丹修士', icon: '🔮', desc: '修为达到金丹期', unlocked: false },
    ],

    // 勋章列表
    badges: [
      { id: 1, name: '学霸', icon: '🎓', desc: '学业认证', unlocked: true },
      { id: 2, name: '诚信', icon: '✅', desc: '信用800+', unlocked: true },
      { id: 3, name: '活跃', icon: '🔥', desc: '连续7天登录', unlocked: false },
    ],

    // 角色列表（默认兜底）
    defaultRoles: [
      { role: 'requester', name: '求道者', icon: '🔍', desc: '发布需求', enabled: true },
      { role: 'provider', name: '传道者', icon: '📜', desc: '提供服务', enabled: true },
      { role: 'mentor', name: '导师', icon: '🐲', desc: '收徒传道', enabled: false },
      { role: 'researcher', name: '研究者', icon: '🔬', desc: '学术研究', enabled: false },
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

      this.setData({
        user,
        currentRole,
        roles: roles.length > 0 ? roles : this.data.defaultRoles,
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

  onRoleTap(e) {
    const { role, enabled } = e.currentTarget.dataset;
    if (!enabled) {
      wx.showToast({ title: '角色未解锁', icon: 'none' });
      return;
    }

    // 已解锁角色 → 切换当前角色
    wx.showLoading({ title: '切换中...' });
    // TODO: 调用API切换角色
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({ title: '角色切换成功', icon: 'success' });
    }, 500);
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
