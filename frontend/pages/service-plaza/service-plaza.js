/**
 * 万务仙坊（服务广场）
 * 路径：pages/service-plaza/service-plaza
 */
const { get } = require('../../utils/request');

Page({
  data: {
    daoFaType: '',
    serviceType: '',  // 传功授法服务类型
    search: '',
    selectedSubject: '',  // 选中的科目
    services: [],
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
    sort: 'hot',
    sortOptions: [
      { value: 'hot',        label: '🔥 综合' },
      { value: 'sales',      label: '📈 销量' },
      { value: 'rating',     label: '⭐ 评分' },
      { value: 'price_asc',  label: '💰 价格低' },
      { value: 'price_desc', label: '💎 价格高' },
    ],
    priceRange: 'all',
    priceOptions: [
      { value: 'all',     label: '全部价格' },
      { value: '0-50',    label: '50灵石以下' },
      { value: '50-100',  label: '50-100灵石' },
      { value: '100-200', label: '100-200灵石' },
      { value: '200-500', label: '200-500灵石' },
      { value: '500+',    label: '500灵石以上' },
    ],
    showFilter: false,
    canPublish: false,
    daoFaList: [
      { id: 'chuan_gong', name: '传功授法', sub: '学科辅导', icon: '📚' },
      { id: 'mi_jing',    name: '联袂问道', sub: '科研组队', icon: '🔬' },
      { id: 'zong_men',   name: '万宗宝鉴', sub: '志愿咨询', icon: '🏫' },
      { id: 'xia_shan',   name: '下山历练', sub: '实习就业', icon: '💼' },
      { id: 'cang_jing',  name: '道藏天阁', sub: '资源社区', icon: '📖' },
    ],
    // 传功授法科目列表（用于筛选）
    chuanGongSubjects: [
      { id: 'math', name: '高等数学', icon: '📐' },
      { id: 'physics', name: '大学物理', icon: '⚡' },
      { id: 'programming', name: '编程/Python', icon: '💻' },
      { id: 'english', name: '英语', icon: '🇬🇧' },
      { id: 'data_structure', name: '数据结构', icon: '🔢' },
      { id: 'acm', name: 'ACM竞赛', icon: '🏆' },
      { id: 'math建模', name: '建模竞赛', icon: '🏆' },
    ],
    // 传功授法服务类型
    serviceTypes: [
      { id: '', name: '全部', icon: '📚' },
      { id: 'tutoring', name: '学科辅导', icon: '📚' },
      { id: 'competition', name: '竞赛陪练', icon: '🏆' },
      { id: 'exam_prep', name: '考前冲刺', icon: '✏️' },
      { id: 'thesis', name: '论文指导', icon: '📄' },
    ],
    // 道法类型 → 显示名称映射
    daoFaNameMap: {
      chuan_gong: '📚 传功授法',
      mi_jing:    '🔬 联袂问道',
      zong_men:   '🏫 万宗宝鉴',
      xia_shan:   '💼 下山历练',
      cang_jing:  '📖 道藏天阁',
    },
  },

  async onLoad(options) {
    if (options.dao_fa_type) {
      this.setData({ daoFaType: options.dao_fa_type });
    }
    await this.checkPublishPermission();
    if (options.action === 'publish') {
      this.onPublishTap();
      return;
    }
    this.loadServices(true);
  },

  onShow() {
    // 刷新服务列表（保持当前筛选状态）
    // 注意：daoFaType 在 onLoad 中通过 URL 参数设置
  },

  async checkPublishPermission() {
    try {
      const user = await get('/auth/me').catch(() => null);
      if (user && user.roles) {
        const canPublish = user.roles.some(
          r => r.enabled && (r.role === 'provider' || r.role === 'elder')
        );
        this.setData({ canPublish });
      }
    } catch (e) {
      console.error('检查发布权限失败', e);
    }
  },

  async loadServices(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, services: [], noMore: false });
    }
    if (this.data.noMore && !reset) return;

    this.setData({ loading: true });
    try {
      const params = {
        page:      this.data.page,
        page_size: this.data.pageSize,
        sort:      this.data.sort,
      };
      if (this.data.daoFaType) params.dao_fa_type = this.data.daoFaType;
      if (this.data.search)    params.search = this.data.search;
      // 传功授法科目筛选
      if (this.data.daoFaType === 'chuan_gong' && this.data.selectedSubject) {
        params.subject = this.data.selectedSubject;
      }
      // 传功授法服务类型筛选
      if (this.data.daoFaType === 'chuan_gong' && this.data.serviceType) {
        params.service_type = this.data.serviceType;
      }
      if (this.data.priceRange !== 'all') {
        const range = this.data.priceRange;
        if (range.endsWith('+')) {
          // 格式 "500+" → 只设置最低价，无上限
          const min = parseInt(range.slice(0, -1));
          if (!isNaN(min)) params.min_price = min * 100;
        } else {
          const parts = range.split('-');
          if (parts[0]) params.min_price = parseInt(parts[0]) * 100;
          if (parts[1]) params.max_price = parseInt(parts[1]) * 100;
        }
      }

      const res = await get('/services', params).catch(e => {
        console.error('加载服务列表失败', e);
        return null;
      });
      if (!res) {
        this.setData({ loading: false });
        return;
      }

      const newList  = (res.services || []).map(s => ({
        ...s,
        _yuanPrice: (s.price / 100).toFixed(2),  // 灵石→元（1元=100灵石）
      }));
      const list     = reset ? newList : [...this.data.services, ...newList];
      const total    = res.total || 0;

      this.setData({
        services:   list,
        total:      total,
        page:       this.data.page + 1,
        noMore:     list.length >= total,
        loading:    false,
        showFilter: false,
      });
    } catch (e) {
      console.error('loadServices error', e);
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    if (!this.data.noMore) this.loadServices();
  },

  onPullDownRefresh() {
    this.loadServices(true).then(() => wx.stopPullDownRefresh()).catch(() => wx.stopPullDownRefresh());
  },

  // 切换道法分类（toggle）
  onDaoFaFilter(e) {
    const type = e.currentTarget.dataset.type;
    // 秘境组队跳转到组队广场
    if (type === 'mi_jing') {
      wx.navigateTo({ url: '/pages/team-plaza/team-plaza' });
      return;
    }
    // 道藏天阁跳转子包
    if (type === 'cang_jing') {
      wx.navigateTo({ url: '/subpackages/jingzang/resource-list/resource-list' });
      return;
    }
    const newType = this.data.daoFaType === type ? '' : type;
    this.setData({
      daoFaType: newType,
      selectedSubject: '',  // 切换道法时清空科目
      serviceType: '',  // 切换道法时清空服务类型
    });
    this.loadServices(true);
  },

  // 切换服务类型（传功授法）
  onServiceTypeChange(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ serviceType: type });
    this.loadServices(true);
  },

  // 切换科目筛选（传功授法）
  onSubjectChange(e) {
    const subject = e.currentTarget.dataset.subject;
    const current = this.data.selectedSubject;
    const newSubject = current === subject ? '' : subject;
    this.setData({ selectedSubject: newSubject });
    this.loadServices(true);
  },

  // 排序变更（bindtap + data-value）
  onSortChange(e) {
    const value = e.currentTarget.dataset.value;
    if (value === this.data.sort) return;
    this.setData({ sort: value });
    this.loadServices(true);
  },

  // 价格筛选变更
  onPriceChange(e) {
    const value = e.currentTarget.dataset.value;
    if (value === this.data.priceRange) return;
    this.setData({ priceRange: value });
    this.loadServices(true);
  },

  // 搜索输入（不自动触发查询）
  onSearchInput(e) {
    this.setData({ search: e.detail.value });
  },

  // 执行搜索
  onSearch() {
    this.loadServices(true);
  },

  // 清除搜索
  onClearSearch() {
    this.setData({ search: '' });
    this.loadServices(true);
  },

  // 切换筛选面板
  onToggleFilter() {
    this.setData({ showFilter: !this.data.showFilter });
  },

  // 重置所有筛选
  onResetFilter() {
    this.setData({
      daoFaType:  '',
      priceRange: 'all',
      sort:       'hot',
      search:     '',
      selectedSubject: '',
      serviceType: '',
      showFilter: false,
    });
    this.loadServices(true);
  },

  // 点击服务卡片
  onServiceTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
  },

  // 发布服务
  onPublishTap() {
    if (!this.data.canPublish) {
      wx.showModal({
        title: '🔒 发布权限不足',
        content: '发布服务需要先成为「🍠 大虾」或「🏛️ 长老」。\n\n解锁条件：\n① 发布 2 个服务 → 自动成为大虾\n② 认证企业邮箱 → 自动成为长老',
        confirmText: '前往解锁',
        cancelText: '我知道了',
        success: (res) => {
          if (res.confirm) {
            wx.switchTab({ url: '/pages/profile/profile' });
          }
        }
      });
      return;
    }
    // 跳转到发布服务页面
    wx.navigateTo({ url: '/pages/publish-service/publish-service' });
  },
});
