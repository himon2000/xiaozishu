/**
 * 下山历练 - 就业资源广场
 * 路径: pages/opportunities/opportunities
 */
const { get, post } = require('../../utils/request');

Page({
  data: {
    categories: [],
    activeCategory: 'job_resource',
    activeGroup: '历练',
    opportunities: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
    search: '',
    // 筛选
    showFilter: false,
    filters: {
      location: '',
      salary: '',
      sort: 'latest',
    },
    locationOptions: ['不限', '北京', '上海', '深圳', '广州', '杭州', '成都', '南京', '武汉', '西安', '远程'],
    salaryOptions: [
      { label: '不限', value: '' },
      { label: '面议', value: 'negotiable' },
      { label: '100以下/天', value: '0-100' },
      { label: '100-200/天', value: '100-200' },
      { label: '200-300/天', value: '200-300' },
      { label: '300+/天', value: '300+' },
      { label: '10K以下/月', value: '0-10k' },
      { label: '10-20K/月', value: '10-20k' },
      { label: '20-30K/月', value: '20-30k' },
      { label: '30K+/月', value: '30k+' },
    ],
    sortOptions: [
      { label: '最新发布', value: 'latest' },
      { label: '最热推荐', value: 'hottest' },
    ],
    // 创建表单
    showCreateModal: false,
    createForm: {
      title: '',
      opportunity_type: 'internship',
      company_name: '',
      position: '',
      position_type: '实习',
      work_location: '',
      work_mode: 'onsite',
      salary_range: '',
      salary_hidden: false,
      description: '',
      requirements: '',
      benefits: '',
      deadline: '',
      apply_url: '',
      contact_wx: '',
      tags: [],
    },
    tagInput: '',
    // 页面模式
    mode: 'explore', // explore|create|manage
  },

  onLoad(options) {
    if (options.category) {
      this.setData({ activeCategory: options.category });
    }
    if (options.mode) {
      this.setData({ mode: options.mode });
    }
    this.loadCategories();
    this.loadOpportunities(true);
  },

  onShow() {
    // 每次显示时刷新
    if (this.data.opportunities.length > 0) {
      this.loadOpportunities(true);
    }
  },

  onPullDownRefresh() {
    this.loadOpportunities(true).then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    this.loadOpportunities();
  },

  // 加载分类
  async loadCategories() {
    try {
      const res = await get('/opportunities/categories');
      this.setData({ categories: res.categories });
    } catch (e) {
      console.error('加载分类失败', e);
    }
  },

  // 加载资源列表
  async loadOpportunities(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, opportunities: [], noMore: false });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });
    try {
      const params = {
        page: this.data.page,
        page_size: this.data.pageSize,
        sort: this.data.filters.sort,
      };
      if (this.data.activeCategory) params.category = this.data.activeCategory;
      if (this.data.search) params.search = this.data.search;
      if (this.data.filters.location) params.location = this.data.filters.location;
      if (this.data.filters.salary) params.salary_range = this.data.filters.salary;

      const res = await get('/opportunities', params);
      const list = reset ? res.opportunities : [...this.data.opportunities, ...res.opportunities];

      this.setData({
        opportunities: list,
        total: res.total,
        page: this.data.page + 1,
        noMore: list.length >= res.total,
        loading: false,
      });
    } catch (e) {
      console.error('加载资源失败', e);
      this.setData({ loading: false });
    }
  },

  // 切换分组
  onGroupChange(e) {
    const group = e.currentTarget.dataset.group;
    this.setData({ activeGroup: group });
  },

  // 切换分类
  onCategoryChange(e) {
    const category = e.currentTarget.dataset.category;
    this.setData({
      activeCategory: category,
      opportunities: [],
      page: 1,
      noMore: false,
    });
    this.loadOpportunities(true);
  },

  // 搜索
  onSearchInput(e) {
    this.setData({ search: e.detail.value });
  },

  onSearch() {
    this.loadOpportunities(true);
  },

  // 筛选
  onToggleFilter() {
    this.setData({ showFilter: !this.data.showFilter });
  },

  onFilterChange(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    const filters = this.data.filters;
    filters[field] = value;
    this.setData({ filters });
  },

  onApplyFilter() {
    this.setData({ showFilter: false });
    this.loadOpportunities(true);
  },

  onResetFilter() {
    this.setData({
      filters: { location: '', salary: '', sort: 'latest' },
    });
  },

  // 点击资源卡片
  onOpportunityTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/opportunity-detail/opportunity-detail?id=${id}` });
  },

  // 收藏/取消收藏
  async onToggleFavorite(e) {
    const { id } = e.currentTarget.dataset;
    const { opportunities } = this.data;
    const index = opportunities.findIndex(o => o.id === id);
    if (index === -1) return;

    try {
      const res = await post(`/opportunities/${id}/favorite`);
      const updated = [...opportunities];
      updated[index] = { ...updated[index], is_favorited: res.is_favorited };
      updated[index].favorite_count += res.is_favorited ? 1 : -1;
      this.setData({ opportunities: updated });
      wx.showToast({
        title: res.is_favorited ? '已收藏' : '已取消收藏',
        icon: 'success'
      });
    } catch (e) {
      wx.showToast({ title: e.detail || '操作失败', icon: 'none' });
    }
  },

  // 打开创建弹窗
  onOpenCreate() {
    this.setData({ showCreateModal: true });
  },

  // 关闭创建弹窗
  onCloseCreate() {
    this.setData({ showCreateModal: false });
  },

  // 更新创建表单
  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    const form = this.data.createForm;
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      form[parent][child] = e.detail.value;
    } else {
      form[field] = e.detail.value;
    }
    this.setData({ createForm: form });
  },

  // 类型选择
  onTypeChange(e) {
    const types = ['internship', 'referral', 'job', 'job_resource'];
    const form = this.data.createForm;
    form.opportunity_type = types[e.detail.value];
    this.setData({ createForm: form });
  },

  // 截止日期
  onDeadlineChange(e) {
    const form = this.data.createForm;
    form.deadline = e.detail.value;
    this.setData({ createForm: form });
  },

  // 标签
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

  // 创建资源
  async onCreateOpportunity() {
    const form = this.data.createForm;
    if (!form.title.trim()) {
      wx.showToast({ title: '请输入资源标题', icon: 'none' });
      return;
    }
    if (!form.description.trim()) {
      wx.showToast({ title: '请输入职位描述', icon: 'none' });
      return;
    }

    try {
      const res = await post('/opportunities', form);
      wx.showToast({ title: '发布成功！', icon: 'success' });
      this.onCloseCreate();
      // 跳转到详情页
      wx.navigateTo({ url: `/pages/opportunity-detail/opportunity-detail?id=${res.id}` });
    } catch (e) {
      wx.showToast({ title: e.detail || '发布失败', icon: 'none' });
    }
  },

  // 页面模式切换
  onModeChange(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({ mode });
    if (mode === 'explore') {
      this.loadOpportunities(true);
    }
  },

  // 获取筛选后的分类
  getFilteredCategories() {
    const { categories, activeGroup } = this.data;
    return categories.filter(c => c.group === activeGroup);
  },
});
