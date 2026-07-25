/**
 * 道友传承模块 - 寻访导师页面
 * 支持企业导师（就业方向）/ 学术导师（学术方向）双轨筛选
 * 路径：subpackages/mentor/find-mentor/find-mentor
 */
const { get, post } = require('../../../utils/request');

Page({
  data: {
    mentors: [],
    page: 1,
    pageSize: 20,
    loading: false,
    noMore: false,
    // 道友传承新增：导师类型筛选
    currentType: 'all',   // 'all' | 'enterprise' | 'academic'
    typeLabels: {
      all: '全部导师',
      enterprise: '企业导师',
      academic: '学术导师',
    },
  },

  onLoad() {
    this.loadMentors(true);
  },

  onTypeChange(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ currentType: type, page: 1, mentors: [], noMore: false });
    this.loadMentors(true);
  },

  async loadMentors(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, mentors: [], noMore: false });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });
    try {
      const params = {
        page: this.data.page,
        page_size: this.data.pageSize,
      };
      // 道友传承：按类型筛选
      if (this.data.currentType !== 'all') {
        params.mentor_type = this.data.currentType;
      }
      const res = await get('/mentorships/mentors', params);

      const list = res.mentors || [];
      const total = res.total || 0;
      const newList = reset ? list : [...this.data.mentors, ...list];

      this.setData({
        mentors: newList,
        page: this.data.page + 1,
        noMore: newList.length >= total,
        loading: false,
      });
    } catch (e) {
      console.error('[寻访导师] 加载失败', e);
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    this.loadMentors();
  },

  onMentorTap(e) {
    const { openid } = e.currentTarget.dataset;
    // 可跳转导师主页或详情
    wx.showToast({ title: '查看导师详情', icon: 'none' });
  },

  async onApplyMentor(e) {
    const { openid, mentortype } = e.currentTarget.dataset;
    // 默认传递当前筛选的导师类型
    const type = mentortype || this.data.currentType;
    const direction = type === 'enterprise' ? 'employment' : 'academic';

    wx.showModal({
      title: '申请传承',
      content: '确定要申请这位导师的道友传承吗？将消耗5修为点。',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          const result = await post('/mentorships/apply', {
            mentor_openid: openid,
            message: '',
            mentor_type: type,
            mentor_direction: direction,
          });
          wx.showToast({ title: result.message || '申请成功', icon: 'success' });
        } catch (e) {
          wx.showToast({ title: e.message || '申请失败', icon: 'none' });
        }
      },
    });
  },

  onBack() {
    wx.navigateBack();
  },

  onShareAppMessage() {
    return {
      title: '🎓 寻访导师 - 小紫薯道途同契',
      path: '/subpackages/mentor/find-mentor/find-mentor',
    };
  },
});
