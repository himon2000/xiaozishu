/**
 * 服务详情页
 * 路径：pages/service-detail/service-detail
 */
const { get, post } = require('../../utils/request');
const { FEATURES } = require('../../config');
const { reportContent } = require('../../utils/report');

Page({
  data: {
    service: null,
    provider: null,
    sessions: 1,
    totalFee: 0,
    loading: true,
    reviewStats: null,
    features: FEATURES,
  },

  onLoad(options) {
    if (options.service_id) {
      this.loadService(options.service_id);
    } else if (options.provider) {
      this.loadProvider(options.provider);
    }
  },

  async loadService(serviceId) {
    try {
      const data = await get(`/services/${serviceId}`);
      const provider = data.provider || {};
      this.setData({
        service: data,
        provider,
        sessions: data.pricing?.min_sessions || 1,
        loading: false,
      });
      this.calcTotal();
      // 加载评价统计
      this.loadReviewStats(serviceId);
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async loadReviewStats(serviceId) {
    try {
      const res = await get(`/reviews/stats/service/${serviceId}`);
      this.setData({ reviewStats: res });
    } catch (e) {
      console.error('加载评价统计失败', e);
    }
  },

  // 查看全部评价
  onViewReviews() {
    const { service } = this.data;
    if (service) {
      wx.navigateTo({
        url: `/pages/review-list/review-list?service_id=${service.id}&title=${encodeURIComponent(service.title)}`,
      });
    }
  },

  async loadProvider(openid) {
    try {
      const data = await get(`/services/provider/${openid}`);
      const provider = data.provider || {};
      this.setData({ provider, loading: false });
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  calcTotal() {
    const { service, sessions } = this.data;
    if (!service) return;
    this.setData({ totalFee: service.pricing.price * sessions });
  },

  onSessionsChange(e) {
    const delta = parseInt(e.currentTarget.dataset.delta);
    const sessions = Math.max((this.data.sessions || 1) + delta, this.data.service?.pricing?.min_sessions || 1);
    this.setData({ sessions });
    this.calcTotal();
  },

  // 查看师傅主页
  onViewMentorProfile() {
    const { provider } = this.data;
    if (provider && provider.openid) {
      wx.navigateTo({
        url: `/subpackages/mentor/mentor-apply/mentor-apply?openid=${provider.openid}`,
      });
    }
  },

  async onBook() {
    if (!FEATURES.payment) {
      wx.showModal({
        title: '预约暂未开放',
        content: '首个公众版本暂不启用支付和付费预约功能。',
        showCancel: false,
      });
      return;
    }
    const { service, sessions } = this.data;
    if (!service) return;

    wx.showLoading({ title: '灵契签订中...' });
    try {
      const order = await post('/orders', {
        service_id: service.id,
        sessions,
      });
      wx.hideLoading();

      wx.showToast({ title: '预约已提交', icon: 'success' });
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: e.message || '下单失败', icon: 'none' });
    }
  },

  onReport() {
    if (this.data.service && this.data.service.id) {
      reportContent('service', this.data.service.id);
    }
  },

  onShareAppMessage() {
    const { service } = this.data;
    return {
      title: service?.title || '来看看这个服务',
      path: `/pages/service-detail/service-detail?service_id=${service?.id}`,
    };
  },
});
