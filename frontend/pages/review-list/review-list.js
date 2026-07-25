/**
 * 服务评价列表
 * 路径: pages/review-list/review-list
 */
const { get } = require('../../utils/request');

Page({
  data: {
    serviceId: '',
    serviceTitle: '',
    reviews: [],
    stats: null,
    page: 1,
    pageSize: 10,
    total: 0,
    loading: false,
    noMore: false,
  },

  onLoad(options) {
    if (options.service_id) {
      this.setData({ serviceId: options.service_id });
      if (options.title) {
        this.setData({ serviceTitle: decodeURIComponent(options.title) });
      }
      this.loadReviews();
      this.loadStats();
    }
  },

  async loadReviews(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, reviews: [], noMore: false });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });
    try {
      const res = await get(`/reviews/service/${this.data.serviceId}`, {
        page: this.data.page,
        page_size: this.data.pageSize,
      });

      const list = reset ? res.reviews : [...this.data.reviews, ...res.reviews];
      this.setData({
        reviews: list,
        total: res.total,
        page: this.data.page + 1,
        noMore: list.length >= res.total,
        loading: false,
      });
    } catch (e) {
      console.error('加载评价失败', e);
      this.setData({ loading: false });
    }
  },

  async loadStats() {
    try {
      const res = await get(`/reviews/stats/service/${this.data.serviceId}`);
      this.setData({ stats: res });
    } catch (e) {
      console.error('加载统计失败', e);
    }
  },

  onReachBottom() {
    this.loadReviews();
  },

  onPullDownRefresh() {
    this.loadReviews(true).then(() => wx.stopPullDownRefresh());
    this.loadStats();
  },
});
