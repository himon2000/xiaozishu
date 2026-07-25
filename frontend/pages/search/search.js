// pages/search/search.js - 全局搜索页面
const { get } = require('../../utils/request');

Page({
  data: {
    searchValue: '',       // 搜索关键词
    historySearch: [],     // 搜索历史
    hotSearch: [
      { id: 1, keyword: 'Python辅导' },
      { id: 2, keyword: '论文润色' },
      { id: 3, keyword: '简历修改' },
      { id: 4, keyword: '考研指导' },
      { id: 5, keyword: '留学咨询' },
      { id: 6, keyword: '竞赛组队' }
    ],                     // 热门搜索
    activeTab: 'service',  // 当前标签：service/services/user/demand
    services: [],          // 服务列表
    users: [],             // 用户列表
    demands: [],           // 需求列表
    loading: false,
    page: 1,
    pageSize: 10,
    hasMore: true
  },

  onLoad(options) {
    // 获取搜索历史
    const history = wx.getStorageSync('searchHistory') || [];
    this.setData({ historySearch: history });

    // 如果有传入关键词，自动搜索
    if (options.keyword) {
      this.setData({ searchValue: options.keyword });
      this.onSearch();
    }
  },

  // 监听搜索输入
  onSearchInput(e) {
    this.setData({ searchValue: e.detail.value });
  },

  // 点击搜索
  onSearch() {
    const keyword = this.data.searchValue.trim();
    if (!keyword) {
      wx.showToast({ title: '请输入搜索关键词', icon: 'none' });
      return;
    }

    // 保存搜索历史
    this.saveSearchHistory(keyword);

    // 执行搜索
    this.doSearch(keyword);
  },

  // 点击历史或热门搜索
  onHistoryTap(e) {
    const keyword = e.currentTarget.dataset.keyword;
    this.setData({ searchValue: keyword });
    this.doSearch(keyword);
  },

  // 执行搜索
  doSearch(keyword) {
    this.setData({ loading: true, page: 1, hasMore: true });

    get('/search', {
      keyword,
      type: this.data.activeTab,
      page: 1,
      page_size: this.data.pageSize
    }).then(res => {
      const { services, users, demands } = res || {};
      this.setData({
        services: services || [],
        users: users || [],
        demands: demands || [],
        loading: false
      });
    }).catch(err => {
      console.error('搜索失败', err);
      this.setData({ loading: false });
      wx.showToast({ title: '搜索失败', icon: 'none' });
    });
  },

  // 保存搜索历史
  saveSearchHistory(keyword) {
    let history = this.data.historySearch;
    // 去重
    history = history.filter(item => item !== keyword);
    // 添加到开头
    history.unshift(keyword);
    // 最多保留10条
    history = history.slice(0, 10);
    this.setData({ historySearch: history });
    wx.setStorageSync('searchHistory', history);
  },

  // 清除搜索历史
  onClearHistory() {
    wx.showModal({
      title: '提示',
      content: '确定清除搜索历史？',
      success: res => {
        if (res.confirm) {
          this.setData({ historySearch: [] });
          wx.removeStorageSync('searchHistory');
        }
      }
    });
  },

  // 切换标签
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab });
    if (this.data.searchValue.trim()) {
      this.doSearch(this.data.searchValue.trim());
    }
  },

  // 加载更多
  onReachBottom() {
    if (!this.data.hasMore || this.data.loading) return;

    const nextPage = this.data.page + 1;
    this.setData({ page: nextPage, loading: true });

    get('/search', {
      keyword: this.data.searchValue,
      type: this.data.activeTab,
      page: nextPage,
      page_size: this.data.pageSize
    }).then(res => {
      const { services, users, demands } = res || {};
      const keyMap = { service: 'services', user: 'users', demand: 'demands' };
      const key = keyMap[this.data.activeTab] || 'services';
      const currentData = this.data[key];
      const nextItems = res[key] || [];
      this.setData({
        [key]: [...currentData, ...nextItems],
        loading: false,
        hasMore: nextItems.length >= this.data.pageSize
      });
    }).catch(err => {
      console.error('加载更多失败', err);
      this.setData({ loading: false });
    });
  },

  // 点击服务卡片
  onServiceTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
  },

  // 点击用户卡片
  onUserTap(e) {
    const openid = e.currentTarget.dataset.openid;
    wx.navigateTo({ url: `/pages/profile/profile?openid=${openid}` });
  },

  // 点击需求卡片
  onDemandTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/service-plaza/service-plaza?view=demands&id=${id}` });
  },

  // 取消返回
  onCancel() {
    wx.navigateBack();
  }
});
