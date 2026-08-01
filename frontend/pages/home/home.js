/**
 * 首页 - 小红书风格
 * 路径：pages/home/home
 */
const { get } = require('../../utils/request');

Page({
  data: {
    viewMode: 'seeker',  // 'seeker' | 'provider'
    hotServices: [],      // 热门服务推荐
    topProviders: [],     // 优秀大虾推荐
    latestDemands: [],    // 最新需求

    // 信息流（小红书瀑布流）
    feedData: [],         // 全部信息流数据
    leftColumn: [],       // 左列瀑布流
    rightColumn: [],      // 右列瀑布流
    feedPage: 1,
    feedPageSize: 10,
    hasMore: true,
    loading: false,
  },

  onLoad() {
    const app = getApp();
    this.setData({ viewMode: (app && app.globalData && app.globalData.viewMode) || 'seeker' });
  },

  async onShow() {
    const tabBar = typeof this.getTabBar === 'function' ? this.getTabBar() : null;
    if (tabBar) tabBar.setData({ selected: 0 });
    const app = getApp();
    this.setData({ viewMode: (app && app.globalData && app.globalData.viewMode) || 'seeker' });
    await this.loadHomeData();
  },

  async onPullDownRefresh() {
    // 重置信息流
    this.setData({
      feedData: [],
      leftColumn: [],
      rightColumn: [],
      feedPage: 1,
      hasMore: true
    });
    await this.loadHomeData();
    wx.stopPullDownRefresh();
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loading) return;
    this.loadMoreFeed();
  },

  // ========== 全局搜索 ==========
  onGlobalSearch() {
    wx.navigateTo({ url: '/pages/search/search' });
  },

  // ========== 6大功能模块跳转 ==========
  onChuanGongTap() {
    wx.navigateTo({ url: '/subpackages/chuan-gong/index/index' });
  },
  onLianMeiTap() {
    wx.navigateTo({ url: '/subpackages/mijing/index/index' });
  },
  onZongMenTap() {
    wx.navigateTo({ url: '/subpackages/zongmen/index/index' });
  },
  onCangJingTap() {
    wx.navigateTo({ url: '/subpackages/jingzang/resource-list/resource-list' });
  },
  onXiaShanTap() {
    wx.navigateTo({ url: '/subpackages/xiashan/index/index' });
  },
  onZhiFaTap() {
    wx.navigateTo({ url: '/pages/dispute-apply/dispute-apply' });
  },

  // ========== 其他跳转 ==========
  onGoToServicePlaza() {
    wx.switchTab({ url: '/pages/service-plaza/service-plaza' });
  },
  onGoToFindMentor() {
    wx.navigateTo({ url: '/subpackages/mentor/find-mentor/find-mentor' });
  },
  onGoToDemandList() {
    wx.navigateTo({ url: '/pages/service-plaza/service-plaza?view=demands' });
  },

  // ========== 信息流点击 ==========
  onFeedTap(e) {
    const { id, type } = e.currentTarget.dataset;
    if (type === 'note') {
      // 笔记当前归入道藏天阁资源详情
      wx.navigateTo({ url: `/subpackages/jingzang/resource-detail/resource-detail?id=${id}` });
    } else if (type === 'service') {
      // 服务详情
      wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
    } else if (type === 'demand') {
      wx.navigateTo({ url: `/pages/service-plaza/service-plaza?view=demands&id=${id}` });
    }
  },

  // ========== 数据加载 ==========
  async loadHomeData() {
    this.setData({ loading: true });
    try {
      const [services, providers, demands, feed] = await Promise.all([
        get('/services?sort=hot&page_size=6').catch(() => null),
        get('/services/providers/top?page_size=6').catch(() => null),
        get('/demands?sort=hot&page_size=3').catch(() => null),
        this.fetchFeedData(1).catch(() => []),
      ]);

      // 分配瀑布流到左右列
      const left = [];
      const right = [];
      feed.forEach((item, index) => {
        if (index % 2 === 0) {
          left.push(item);
        } else {
          right.push(item);
        }
      });

      this.setData({
        hotServices: (services && services.services) || [],
        topProviders: (providers && providers.providers) || [],
        latestDemands: (demands && demands.demands) || [],
        feedData: feed,
        leftColumn: left,
        rightColumn: right,
        loading: false,
      });
    } catch (e) {
      console.error('加载首页失败', e);
      this.setData({ loading: false });
    }
  },

  async fetchFeedData(page) {
    // 调用后端信息流接口
    const res = await get(`/feed?page=${page}&page_size=${this.data.feedPageSize}`).catch(() => null);
    return (res && res.items) || [];
  },

  async loadMoreFeed() {
    if (!this.data.hasMore) return;

    this.setData({ loading: true });
    const nextPage = this.data.feedPage + 1;

    try {
      const newItems = await this.fetchFeedData(nextPage);
      if (newItems.length === 0) {
        this.setData({ hasMore: false, loading: false });
        return;
      }

      // 追加到信息流
      const allFeed = [...this.data.feedData, ...newItems];

      // 重新分配瀑布流
      const left = [];
      const right = [];
      allFeed.forEach((item, index) => {
        if (index % 2 === 0) {
          left.push(item);
        } else {
          right.push(item);
        }
      });

      this.setData({
        feedData: allFeed,
        leftColumn: left,
        rightColumn: right,
        feedPage: nextPage,
        hasMore: newItems.length >= this.data.feedPageSize,
        loading: false,
      });
    } catch (e) {
      console.error('加载更多失败', e);
      this.setData({ loading: false });
    }
  },

  // ========== 事件处理 ==========
  onServiceTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
  },

  onProviderTap(e) {
    const { openid } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?provider=${openid}` });
  },

  onDemandTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-plaza/service-plaza?view=demands&id=${id}` });
  },

  onShareAppMessage() {
    const app = getApp();
    return {
      title: '小紫薯·明明相代校园接力平台，学长带你飞升！',
      path: `/pages/home/home?ref=${(app.globalData.userInfo && app.globalData.userInfo.referral_code) || ''}`,
    };
  },

  onShareTimeline() {
    return {
      title: '小紫薯·明明相代校园接力平台',
    };
  },
});
