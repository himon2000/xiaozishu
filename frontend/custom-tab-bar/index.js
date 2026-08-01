/**
 * 自定义TabBar组件
 * 小红书风格：中间紫色"+"按钮
 * 路径：custom-tab-bar/index
 */
Component({
  data: {
    selected: 0,
    showCreateModal: false,
    createOptions: [
      { id: 'service', icon: '📚', name: '发布服务', desc: '成为传功者，分享你的技能' },
      { id: 'demand', icon: '📝', name: '发布需求', desc: '发布求助需求，快速匹配' },
      { id: 'note', icon: '📕', name: '发布笔记', desc: '分享学习心得、经验攻略' },
      { id: 'team', icon: '👥', name: '发起组队', desc: '创建课题/竞赛/活动组队' },
    ],
  },

  attached() {
    this.setSelectedTab();
  },

  pageLifetimes: {
    show() {
      this.setSelectedTab();
    },
  },

  methods: {
    // 设置选中的Tab
    setSelectedTab() {
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      const route = currentPage && (currentPage.route || currentPage.__route__);

      const tabMap = {
        'pages/home/home': 0,
        'pages/service-plaza/service-plaza': 1,
        'pages/order-list/order-list': 2,
        'pages/profile/profile': 3,
      };

      if (route && Object.prototype.hasOwnProperty.call(tabMap, route)) {
        this.setData({ selected: tabMap[route] });
      }
    },

    // Tab切换
    onTabTap(e) {
      const index = e.currentTarget.dataset.index;
      if (index === this.data.selected) return;

      const routes = [
        '/pages/home/home',
        '/pages/service-plaza/service-plaza',
        '/pages/order-list/order-list',
        '/pages/profile/profile',
      ];

      wx.switchTab({ url: routes[index] });
    },

    // 中间"+"按钮点击
    onCreateTap() {
      this.setData({ showCreateModal: true });
    },

    // 关闭创建弹窗
    onModalClose() {
      this.setData({ showCreateModal: false });
    },

    // 选择创建类型
    onCreateSelect(e) {
      const { type } = e.currentTarget.dataset;
      this.setData({ showCreateModal: false });

      const routes = {
        service: '/pages/publish-service/publish-service',
        demand: '/pages/publish-demand/publish-demand',
        note: '/subpackages/jingzang/publish-resource/publish-resource',
        team: '/pages/team-plaza/team-plaza?action=create',
      };

      if (routes[type]) {
        wx.navigateTo({ url: routes[type] });
      } else {
        wx.showToast({ title: '功能开发中', icon: 'none' });
      }
    },
  },
});
