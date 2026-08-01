/**
 * 传功授法 - 首页
 * 学科辅导/竞赛陪练/论文指导 独立入口
 * 路径：subpackages/chuan-gong/index/index
 */
const { get } = require('../../../utils/request');

Page({
  data: {
    // 热门科目（快捷入口）
    hotSubjects: [
      { id: 'math', name: '高等数学', icon: '📐', count: 128 },
      { id: 'programming', name: '编程/Python', icon: '💻', count: 96 },
      { id: 'english', name: '英语四六级', icon: '🇬🇧', count: 85 },
      { id: 'physics', name: '大学物理', icon: '⚡', count: 72 },
      { id: 'linear_algebra', name: '线性代数', icon: '📊', count: 68 },
      { id: 'probability', name: '概率论', icon: '🎲', count: 54 },
    ],
    // 服务类型
    serviceTypes: [
      { id: '', name: '全部', icon: '📚' },
      { id: 'tutoring', name: '学科辅导', icon: '📖' },
      { id: 'competition', name: '竞赛陪练', icon: '🏆' },
      { id: 'exam_prep', name: '考前冲刺', icon: '✏️' },
      { id: 'thesis', name: '论文指导', icon: '📄' },
    ],
    // 当前选中的服务类型
    currentType: '',
    // 热门导师
    topMentors: [],
    // 热门服务
    hotServices: [],
    // 筛选参数
    selectedSubject: '',
    selectedType: '',
    loading: true,
    canPublish: false,
  },

  onLoad(options) {
    // 支持外部传入筛选参数
    if (options.subject) {
      this.setData({ selectedSubject: options.subject });
    }
    if (options.type) {
      this.setData({ currentType: options.type });
    }
    this.loadData();
  },

  onShow() {
    this.checkPublishPermission();
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

  async loadData() {
    this.setData({ loading: true });
    try {
      const [mentorsRes, servicesRes] = await Promise.all([
        get('/services/providers/top', { dao_fa_type: 'chuan_gong', page_size: 6 }).catch(() => null),
        get('/services/hot', { dao_fa_type: 'chuan_gong', limit: 4 }).catch(() => null),
      ]);

      this.setData({
        topMentors: (mentorsRes && mentorsRes.providers) || [],
        hotServices: (servicesRes && servicesRes.services) || [],
        loading: false,
      });
    } catch (e) {
      console.error('加载数据失败', e);
      this.setData({ loading: false });
    }
  },

  // ========== 科目选择 ==========
  onSubjectTap(e) {
    const { subject } = e.currentTarget.dataset;
    const url = `/subpackages/chuan-gong/search/search?subject=${subject}`;
    wx.navigateTo({ url });
  },

  // ========== 类型筛选 ==========
  onTypeChange(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ currentType: type });
    // 刷新数据
    this.loadFilteredData();
  },

  async loadFilteredData() {
    const params = { dao_fa_type: 'chuan_gong', limit: 10 };
    if (this.data.currentType) {
      params.service_type = this.data.currentType;
    }
    try {
      const res = await get('/services', params).catch(() => null);
      if (res && res.services) {
        this.setData({ hotServices: res.services.slice(0, 4) });
      }
    } catch (e) {
      console.error('加载筛选数据失败', e);
    }
  },

  // ========== 快捷操作 ==========
  onViewAllMentors() {
    wx.navigateTo({ url: '/subpackages/chuan-gong/search/search?tab=mentors' });
  },

  onViewAllServices() {
    const url = '/subpackages/chuan-gong/search/search';
    wx.navigateTo({ url });
  },

  // ========== 发布需求 ==========
  onPublishRequest() {
    if (!this.data.canPublish) {
      wx.showModal({
        title: '🔒 发布权限',
        content: '成为宗门弟子后才能发布传功服务',
        confirmText: '去认证',
        success: (res) => {
          if (res.confirm) {
            wx.switchTab({ url: '/pages/profile/profile' });
          }
        }
      });
      return;
    }
    wx.navigateTo({ url: '/pages/publish-service/publish-service' });
  },

  // ========== 跳转到通用搜索页 ==========
  onSearchTap() {
    wx.navigateTo({ url: '/subpackages/chuan-gong/search/search' });
  },

  // ========== 卡片点击 ==========
  onMentorTap(e) {
    const { openid } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?provider=${openid}` });
  },

  onServiceTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/service-detail/service-detail?service_id=${id}` });
  },

  // ========== 分享配置 ==========
  onShareAppMessage() {
    return {
      title: '📚 传功授法 - 找学长带你飞升！',
      path: '/subpackages/chuan-gong/index/index',
    };
  },
});
