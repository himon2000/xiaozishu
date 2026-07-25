/**
 * 万宗宝鉴 - 首页（志愿咨询）
 * 院校咨询/志愿填报/名校攻略
 * 路径：subpackages/zongmen/index/index
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    // 院校层次
    schoolTiers: [
      { id: 'top', name: '顶尖985', icon: '🏰' },
      { id: '985', name: '普通985', icon: '🏛️' },
      { id: '211', name: '211院校', icon: '🎓' },
      { id: 'pass', name: '一本院校', icon: '📚' },
    ],
    // 热门服务
    services: [],
    loading: true,
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const res = await get('/services', {
        dao_fa_type: 'zong_men',
        sort: 'hot',
        page_size: 6
      }).catch(() => null);
      this.setData({
        services: (res && res.services) || [],
        loading: false,
      });
    } catch (e) {
      console.error('加载数据失败', e);
      this.setData({ loading: false });
    }
  },

  onTierTap(e) {
    const { tier } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-plaza/service-plaza?dao_fa_type=zong_men&tier=${tier}` });
  },

  onServiceTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
  },

  onViewAll() {
    wx.navigateTo({ url: `/pages/service-plaza/service-plaza?dao_fa_type=zong_men` });
  },

  // 发起咨询需求
  onPublishConsult() {
    wx.navigateTo({ url: `/subpackages/zongmen/publish/publish?tier=${this.data.targetTier || ''}` });
  },

  onShareAppMessage() {
    return {
      title: '🏫 万宗宝鉴 - 名校学长带你飞！',
      path: '/subpackages/zongmen/index/index',
    };
  },
});
