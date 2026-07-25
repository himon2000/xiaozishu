/**
 * 传功授法 - 搜索页
 * 导师和服务搜索 + 筛选
 * 路径：subpackages/chuan-gong/search/search
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    // 搜索相关
    search: '',
    tab: 'services',  // 'services' | 'mentors'

    // 筛选参数
    selectedSubject: '',
    selectedType: '',
    minLevel: 0,
    sort: 'hot',

    // 科目列表
    subjects: [
      { id: 'math', name: '高等数学', icon: '📐' },
      { id: 'linear_algebra', name: '线性代数', icon: '📊' },
      { id: 'probability', name: '概率论', icon: '🎲' },
      { id: 'physics', name: '大学物理', icon: '⚡' },
      { id: 'programming', name: '编程/Python', icon: '💻' },
      { id: 'data_structure', name: '数据结构', icon: '🔢' },
      { id: 'english', name: '英语四六级', icon: '🇬🇧' },
      { id: 'economics', name: '经济学', icon: '💹' },
      { id: 'math建模', name: '数学建模', icon: '🏆' },
      { id: 'acm', name: 'ACM竞赛', icon: '🏆' },
      { id: 'postgraduate', name: '考研辅导', icon: '🎓' },
      { id: 'thesis', name: '论文指导', icon: '📄' },
    ],

    // 服务类型
    serviceTypes: [
      { id: '', name: '全部', icon: '📚' },
      { id: 'tutoring', name: '学科辅导', icon: '📖' },
      { id: 'competition', name: '竞赛陪练', icon: '🏆' },
      { id: 'exam_prep', name: '考前冲刺', icon: '✏️' },
      { id: 'thesis', name: '论文指导', icon: '📄' },
    ],

    // 排序选项
    sortOptions: [
      { value: 'hot', label: '🔥 综合' },
      { value: 'rating', label: '⭐ 评分' },
      { value: 'sales', label: '📈 销量' },
      { value: 'price_asc', label: '💰 价格低' },
      { value: 'price_desc', label: '💎 价格高' },
    ],

    // 数据
    services: [],
    mentors: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
    showFilter: false,
  },

  onLoad(options) {
    if (options.subject) {
      this.setData({ selectedSubject: options.subject });
    }
    if (options.type) {
      this.setData({ selectedType: options.type });
    }
    if (options.tab) {
      this.setData({ tab: options.tab });
    }
    if (options.search) {
      this.setData({ search: options.search });
    }
    this.loadData(true);
  },

  // ========== Tab 切换 ==========
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab, page: 1, services: [], mentors: [], noMore: false });
    this.loadData(true);
  },

  // ========== 搜索 ==========
  onSearchInput(e) {
    this.setData({ search: e.detail.value });
  },

  onSearch() {
    this.setData({ page: 1, services: [], mentors: [], noMore: false });
    this.loadData(true);
  },

  // ========== 筛选 ==========
  onToggleFilter() {
    this.setData({ showFilter: !this.data.showFilter });
  },

  onSubjectChange(e) {
    const subject = e.currentTarget.dataset.subject;
    const newSubject = this.data.selectedSubject === subject ? '' : subject;
    this.setData({ selectedSubject: newSubject });
  },

  onTypeChange(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ selectedType: type });
  },

  onSortChange(e) {
    const sort = e.currentTarget.dataset.value;
    this.setData({ sort });
  },

  onLevelChange(e) {
    const level = e.currentTarget.dataset.level;
    this.setData({ minLevel: level });
  },

  onResetFilter() {
    this.setData({
      selectedSubject: '',
      selectedType: '',
      minLevel: 0,
      sort: 'hot',
      showFilter: false,
    });
  },

  onApplyFilter() {
    this.setData({ showFilter: false, page: 1, services: [], mentors: [], noMore: false });
    this.loadData(true);
  },

  // ========== 数据加载 ==========
  async loadData(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, noMore: false });
    }
    if (this.data.noMore && !reset) return;

    this.setData({ loading: true });
    try {
      const params = {
        page: this.data.page,
        page_size: this.data.pageSize,
        dao_fa_type: 'chuan_gong',
        sort: this.data.sort,
      };

      if (this.data.search) params.search = this.data.search;
      if (this.data.selectedSubject) params.subject = this.data.selectedSubject;
      if (this.data.selectedType) params.service_type = this.data.selectedType;
      if (this.data.minLevel > 0) params.min_level = this.data.minLevel;

      if (this.data.tab === 'services') {
        const res = await get('/services', params).catch(() => null);
        if (res) {
          const newList = res.services || [];
          const list = reset ? newList : [...this.data.services, ...newList];
          this.setData({
            services: list,
            total: res.total || 0,
            page: this.data.page + 1,
            noMore: list.length >= (res.total || 0),
          });
        }
      } else {
        const res = await get('/services/providers/top', params).catch(() => null);
        if (res) {
          const newList = res.providers || [];
          const list = reset ? newList : [...this.data.mentors, ...newList];
          this.setData({
            mentors: list,
            total: res.total || 0,
            page: this.data.page + 1,
            noMore: list.length >= (res.total || 0),
          });
        }
      }
    } catch (e) {
      console.error('加载数据失败', e);
    } finally {
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    if (!this.data.noMore) this.loadData();
  },

  // ========== 卡片点击 ==========
  onServiceTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
  },

  onMentorTap(e) {
    const { openid } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?provider=${openid}` });
  },
});
