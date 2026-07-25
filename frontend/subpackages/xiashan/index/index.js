/**
 * 下山历练 - 首页（实习就业）
 * 实习内推/名企兼职/就业指导
 * 路径：subpackages/xiashan/index/index
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    // 岗位类型
    jobTypes: [
      { id: 'intern', name: '实习岗位', icon: '💼' },
      { id: 'parttime', name: '兼职', icon: '📋' },
      { id: 'fulltime', name: '全职', icon: '🏢' },
      { id: 'referral', name: '内推', icon: '🎯' },
    ],
    // 热门机会
    opportunities: [],
    loading: true,
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const res = await get('/opportunities', {
        dao_fa_type: 'xia_shan',
        sort: 'hot',
        page_size: 10
      }).catch(() => null);
      this.setData({
        opportunities: (res && res.opportunities) || [],
        loading: false,
      });
    } catch (e) {
      console.error('加载数据失败', e);
      this.setData({ loading: false });
    }
  },

  onTypeTap(e) {
    const { type } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/opportunities/opportunities?type=${type}` });
  },

  onOpportunityTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/opportunity-detail/opportunity-detail?id=${id}` });
  },

  onViewAll() {
    wx.navigateTo({ url: '/pages/opportunities/opportunities' });
  },

  // 发布历练机会
  onPublishOpportunity() {
    wx.navigateTo({ url: `/subpackages/xiashan/publish/publish?type=${this.data.jobType || ''}` });
  },

  onShareAppMessage() {
    return {
      title: '💼 下山历练 - 名企实习机会！',
      path: '/subpackages/xiashan/index/index',
    };
  },
});
