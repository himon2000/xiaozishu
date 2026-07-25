/**
 * 联袂问道 - 我的问道之旅
 * 路径: pages/my-teams/my-teams
 * 道籍玉牒 → 个人中心 → 联袂问道(组队)
 */
const { get } = require('../../utils/request');
const app = getApp();

Page({
  data: {
    activeTab: 'created', // created(发起) | joined(加入)
    created: [],
    joined: [],
    loading: false,
    tabs: [
      { key: 'created', label: '🔱 我发起的' },
      { key: 'joined', label: '🤝 我加入的' },
    ],
  },

  onLoad(options) {
    // 如果有tab参数，优先使用
    if (options.tab) {
      this.setData({ activeTab: options.tab });
    }
  },

  onShow() {
    this.loadMyTeams();
  },

  async loadMyTeams() {
    this.setData({ loading: true });
    try {
      const res = await get('/teams/my');
      this.setData({
        created: res.created || [],
        joined: res.joined || [],
        loading: false,
      });
    } catch (e) {
      console.error('加载我的组队失败', e);
      app.handleError(e, '加载失败');
      this.setData({ loading: false });
    }
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab });
  },

  onTeamTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/team-detail/team-detail?team_id=${id}` });
  },

  goToPlaza() {
    wx.navigateTo({ url: '/pages/team-plaza/team-plaza' });
  },

  onPullDownRefresh() {
    this.loadMyTeams().then(() => wx.stopPullDownRefresh());
  },
});
