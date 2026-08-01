/**
 * 个人中心 - 我的页面 列表菜单式
 * 路径：pages/profile/profile
 *
 * 模块列表：
 * 1. 用户信息卡片 - 头像/昵称/角色/学校/统计
 * 2. 功能菜单列表（列表菜单式）
 * 3. 设置与账户
 */
const { get, post } = require('../../utils/request');
const { FEATURES } = require('../../config');

Page({
  data: {
    user: null,
    currentRole: null,
    roles: [],
    loading: true,

    // 统计数据
    orderStats: { total: 0, pending: 0, in_progress: 0, completed: 0 },
    serviceStats: { total: 0, active: 0, completed: 0, rating: '5.0' },
    taskStats: { pending: 0 },  // 我的任务待办角标
    viewOpenid: '',
    features: FEATURES,
  },

  onLoad(options) {
    this.setData({ viewOpenid: options.openid || '' });
    if (options.action === 'cert') {
      this.setData({ showCertTab: true });
    }
  },

  async onShow() {
    const tabBar = typeof this.getTabBar === 'function' ? this.getTabBar() : null;
    if (tabBar) tabBar.setData({ selected: 3 });
    await this.loadProfile();
  },

  // ========== 数据加载 ==========

  async loadProfile() {
    this.setData({ loading: true });
    try {
      const isOtherUser = Boolean(this.data.viewOpenid);
      const userEndpoint = isOtherUser
        ? `/auth/users/profile/${encodeURIComponent(this.data.viewOpenid)}`
        : '/auth/me';
      const [userRes, ordersRes, servicesRes] = await Promise.all([
        get(userEndpoint).catch(() => null),
        isOtherUser ? Promise.resolve(null) : get('/orders?page_size=20').catch(() => null),
        isOtherUser ? Promise.resolve(null) : get('/services/mine?page_size=50').catch(() => null),
      ]);

      const user = userRes || {};
      const roles = (user.roles) || [];
      const currentRole = (user.current_role_obj) || (roles.length > 0 ? roles.find(r => r.enabled) : null);

      // 处理订单数据
      const orders = (ordersRes && ordersRes.orders) || [];
      const orderStats = this.calculateOrderStats(orders);

      // 处理服务数据
      const services = (servicesRes && servicesRes.services) || [];
      const serviceStats = this.calculateServiceStats(services);

      this.setData({
        user: user,
        currentRole: currentRole,
        roles: roles,
        orderStats: orderStats,
        serviceStats: serviceStats,
        loading: false,
      });
    } catch (e) {
      console.error('加载个人信息失败', e);
      this.setData({ loading: false });
    }
  },

  calculateOrderStats(orders) {
    const stats = { total: orders.length, pending: 0, in_progress: 0, completed: 0 };
    orders.forEach(order => {
      if (order.status === 'pending_payment') stats.pending++;
      else if (order.status === 'paid' || order.status === 'in_progress') stats.in_progress++;
      else if (order.status === 'completed') stats.completed++;
    });
    return stats;
  },

  calculateServiceStats(services) {
    const stats = { total: services.length, active: 0, completed: 0, rating: '5.0' };
    let totalRating = 0, ratedCount = 0;
    services.forEach(service => {
      if (service.status === 'active' || service.status === 'online') stats.active++;
      else if (service.status === 'completed') stats.completed++;
      if (service.rating) {
        totalRating += parseFloat(service.rating);
        ratedCount++;
      }
    });
    if (ratedCount > 0) stats.rating = (totalRating / ratedCount).toFixed(1);
    return stats;
  },

  getExpNeededForLevel(level) {
    return 100 + (level - 1) * 50;
  },

  // ========== 菜单跳转 ==========

  // 我的弟子
  onMyDisciples() {
    wx.navigateTo({ url: '/subpackages/mentor/my-disciples/my-disciples' });
  },

  // 均利道池
  onDividendPool() {
    wx.navigateTo({ url: '/pages/dividend-pool/dividend-pool' });
  },

  // 道藏天阁
  onJingzang() {
    wx.navigateTo({ url: '/subpackages/jingzang/resource-list/resource-list' });
  },

  // 万宗宝鉴
  onSchoolWiki() {
    wx.navigateTo({ url: '/subpackages/jingzang/school-wiki/school-wiki' });
  },

  // 我的历练（就业资源）
  onMyOpportunities() {
    wx.navigateTo({ url: '/pages/my-opportunities/my-opportunities' });
  },

  // 我的任务（课题/项目等待办）
  onMyTasks() {
    wx.showToast({ title: '任务功能暂未开放', icon: 'none' });
  },

  // 我的传承树（师徒关系树）
  onMyLineage() {
    wx.navigateTo({ url: '/subpackages/mentor/lineage-tree/lineage-tree' });
  },

  // 我的客服
  onCustomerService() {
    wx.navigateTo({ url: '/pages/customer-service/customer-service' });
  },

  onPublishService() {
    wx.navigateTo({ url: '/pages/publish-service/publish-service' });
  },

  onPublishDemand() {
    wx.navigateTo({ url: '/pages/publish-demand/publish-demand' });
  },

  onFindMentor() {
    wx.navigateTo({ url: '/subpackages/mentor/find-mentor/find-mentor' });
  },

  onMyTeams() {
    wx.navigateTo({ url: '/pages/my-teams/my-teams' });
  },

  // ========== 功能模块跳转 ==========

  // 我的订单
  onMyOrders() {
    wx.switchTab({ url: '/pages/order-list/order-list' });
  },

  // 我的服务
  onMyServices() {
    wx.navigateTo({ url: '/pages/service-plaza/service-plaza?view=mine' });
  },

  // 我的修为
  onMyCultivation() {
    wx.navigateTo({ url: '/pages/cultivation/cultivation' });
  },

  // 我的成长/修为
  onGrowthDetail() {
    wx.navigateTo({ url: '/subpackages/profile/growth-detail/growth-detail?tab=growth' });
  },

  // 我的资产
  onMyAsset() {
    wx.showToast({ title: '支付功能暂未开放', icon: 'none' });
  },

  // 我的课题
  onMyResearch() {
    wx.navigateTo({ url: '/pages/my-research/my-research' });
  },

  // 我的传承树
  onMyMentorship() {
    wx.navigateTo({ url: '/subpackages/mentor/lineage-tree/lineage-tree' });
  },

  // 我的飞花令
  onFeihuaDetail() {
    wx.navigateTo({ url: '/subpackages/profile/referral-code/referral-code' });
  },

  // ========== 用户信息 ==========

  onAvatarTap() {
    wx.previewImage({
      urls: [this.data.user?.avatar_url || '/assets/default-avatar.png'],
    });
  },

  onEditProfile() {
    wx.navigateTo({ url: '/pages/edit-profile/edit-profile' });
  },

  onMyRole() {
    wx.navigateTo({ url: '/subpackages/profile/growth-detail/growth-detail?tab=role' });
  },

  // ========== 菜单 ==========

  onMenuTap(e) {
    const { url } = e.currentTarget.dataset;
    if (!url) {
      wx.showToast({ title: '功能开发中', icon: 'none' });
      return;
    }
    const tabBarPages = ['/pages/home/home', '/pages/service-plaza/service-plaza', '/pages/order-list/order-list', '/pages/profile/profile'];
    if (tabBarPages.includes(url)) {
      wx.switchTab({ url });
    } else {
      wx.navigateTo({ url });
    }
  },

  // ========== 退出登录 ==========

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          getApp()?.clearSession?.();
          wx.reLaunch({ url: '/pages/splash/splash' });
        }
      },
    });
  },
});
