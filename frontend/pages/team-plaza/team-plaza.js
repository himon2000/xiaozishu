/**
 * 秘境组队 - 组队广场
 * 路径: pages/team-plaza/team-plaza
 */
const { get, post } = require('../../utils/request');

Page({
  data: {
    categories: [],
    activeCategory: 'mi_jing',
    teams: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
    search: '',
    showCreateModal: false,
    // 创建表单
    createForm: {
      title: '',
      description: '',
      category: 'mi_jing',
      max_members: 5,
      tags: [],
      target_date: '',
      deadline: '',
    },
    tagInput: '',
  },

  onLoad(options) {
    if (options.category) {
      this.setData({ activeCategory: options.category });
    }
    this.loadCategories();
    this.loadTeams(true);
    // 从"发起组队"入口直接打开创建弹窗
    if (options.action === 'create') {
      this.setData({ showCreateModal: true });
    }
  },

  async loadCategories() {
    try {
      const res = await get('/teams/categories');
      this.setData({ categories: res.categories });
    } catch (e) {
      console.error('加载分类失败', e);
    }
  },

  async loadTeams(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, teams: [], noMore: false });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });
    try {
      const params = {
        page: this.data.page,
        page_size: this.data.pageSize,
        category: this.data.activeCategory,
      };
      if (this.data.search) params.search = this.data.search;

      const res = await get('/teams', params);
      const list = reset ? res.teams : [...this.data.teams, ...res.teams];

      this.setData({
        teams: list,
        total: res.total,
        page: this.data.page + 1,
        noMore: list.length >= res.total,
        loading: false,
      });
    } catch (e) {
      console.error('加载组队失败', e);
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    this.loadTeams();
  },

  onPullDownRefresh() {
    this.loadTeams(true).then(() => wx.stopPullDownRefresh());
  },

  // 切换分类
  onCategoryChange(e) {
    const category = e.currentTarget.dataset.category;
    this.setData({ activeCategory: category, teams: [] });
    this.loadTeams(true);
  },

  // 搜索
  onSearchInput(e) {
    this.setData({ search: e.detail.value });
  },

  onSearch() {
    this.loadTeams(true);
  },

  // 打开创建组队弹窗
  onOpenCreate() {
    this.setData({ showCreateModal: true });
  },

  // 关闭创建弹窗
  onCloseCreate() {
    this.setData({ showCreateModal: false, createForm: { category: this.data.activeCategory, max_members: 5 } });
  },

  // 更新创建表单
  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    const form = this.data.createForm;
    form[field] = e.detail.value;
    this.setData({ createForm: form });
  },

  // 截止日期选择
  onDeadlineChange(e) {
    const form = this.data.createForm;
    form.deadline = e.detail.value;
    this.setData({ createForm: form });
  },

  // 人数选择
  onMaxMembersChange(e) {
    const form = this.data.createForm;
    form.max_members = parseInt(e.detail.value) + 2; // 2-10人
    this.setData({ createForm: form });
  },

  // 标签输入
  onTagInput(e) {
    this.setData({ tagInput: e.detail.value });
  },

  onAddTag() {
    const tag = this.data.tagInput.trim();
    if (!tag) return;
    const form = this.data.createForm;
    if (form.tags.length >= 5) {
      wx.showToast({ title: '最多5个标签', icon: 'none' });
      return;
    }
    form.tags.push(tag);
    this.setData({ createForm: form, tagInput: '' });
  },

  onRemoveTag(e) {
    const index = e.currentTarget.dataset.index;
    const form = this.data.createForm;
    form.tags.splice(index, 1);
    this.setData({ createForm: form });
  },

  // 创建组队
  async onCreateTeam() {
    const form = this.data.createForm;
    if (!form.title.trim()) {
      wx.showToast({ title: '请输入组队名称', icon: 'none' });
      return;
    }
    if (!form.description.trim()) {
      wx.showToast({ title: '请输入组队描述', icon: 'none' });
      return;
    }

    try {
      const res = await post('/teams', form);
      wx.showToast({ title: '创建成功！', icon: 'success' });
      this.onCloseCreate();
      // 跳转到组队详情
      wx.navigateTo({ url: `/pages/team-detail/team-detail?team_id=${res.id}` });
    } catch (e) {
      wx.showToast({ title: e.detail || '创建失败', icon: 'none' });
    }
  },

  // 点击组队卡片
  onTeamTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/team-detail/team-detail?team_id=${id}` });
  },

  // 跳转到就业资源广场
  goToOpportunities() {
    wx.navigateTo({ url: '/pages/opportunities/opportunities' });
  },
});
