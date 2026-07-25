/**
 * 联袂问道 - 首页（科研组队）
 * 课题带教/科研合作
 * 路径：subpackages/mijing/index/index
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    // 热门课题分类
    categories: [
      { id: 'research', name: '科研项目', icon: '🔬' },
      { id: 'innovation', name: '创新创业', icon: '💡' },
      { id: 'competition', name: '学科竞赛', icon: '🏆' },
      { id: 'paper', name: '论文发表', icon: '📄' },
    ],
    // 招募中的课题
    teams: [],
    loading: true,
    canPublish: false,
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const res = await get('/teams', { dao_fa_type: 'mi_jing', page_size: 10 }).catch(() => null);
      this.setData({
        teams: (res && res.teams) || [],
        loading: false,
      });
    } catch (e) {
      console.error('加载数据失败', e);
      this.setData({ loading: false });
    }
  },

  onCategoryTap(e) {
    const { category } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/team-plaza/team-plaza?category=${category}` });
  },

  onTeamTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/team-detail/team-detail?team_id=${id}` });
  },

  onViewAll() {
    wx.navigateTo({ url: '/pages/team-plaza/team-plaza' });
  },

  onPublish() {
    wx.navigateTo({ url: '/pages/team-plaza/team-plaza?action=create' });
  },

  onShareAppMessage() {
    return {
      title: '🔬 联袂问道 - 找队友一起搞科研！',
      path: '/subpackages/mijing/index/index',
    };
  },
});
