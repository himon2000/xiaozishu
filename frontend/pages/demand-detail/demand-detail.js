/**
 * 需求详情页
 * 路径：pages/demand-detail/demand-detail
 * 由搜索结果 / 服务广场需求分栏跳转，参数 demand_id
 */
const { get } = require('../../utils/request');

const TYPE_NAMES = {
  tutor: '找辅导',
  team: '找队友',
  internship: '找实习',
  consult: '志愿咨询',
  mentor: '找导师',
};

const STATUS_NAMES = {
  open: '招募中',
  closed: '已关闭',
  matched: '已匹配',
  cancelled: '已取消',
};

Page({
  data: {
    demand: null,
    loading: true,
    errorText: '',
  },

  onLoad(options) {
    const demandId = options.demand_id || options.id;
    if (!demandId) {
      this.setData({ loading: false, errorText: '缺少需求编号' });
      return;
    }
    this.loadDemand(demandId);
  },

  async loadDemand(demandId) {
    try {
      const data = await get(`/demands/${demandId}`);
      if (!data || data.success === false || !data.id) {
        this.setData({
          loading: false,
          demand: null,
          errorText: (data && data.message) || '需求不存在或已下架',
        });
        return;
      }
      this.setData({
        demand: this.normalize(data),
        loading: false,
        errorText: '',
      });
    } catch (e) {
      console.error('加载需求详情失败', e);
      this.setData({ loading: false, demand: null, errorText: '加载失败，请稍后重试' });
    }
  },

  // 字段归一：后端 budget 为灵石整数，0 表示免费互助
  normalize(raw) {
    const budget = Number(raw.budget || 0);
    const typeName = raw.typeName || TYPE_NAMES[raw.demand_type || raw.type] || '通用需求';
    return {
      ...raw,
      typeName,
      statusText: STATUS_NAMES[raw.status] || '招募中',
      isFree: budget === 0,
      budgetText: budget === 0 ? '免费互助' : `${budget} 灵石`,
      createdText: String(raw.created_at || '').replace('T', ' ').slice(0, 16),
      tags: raw.tags || [],
    };
  },

  onContact() {
    const contact = this.data.demand && this.data.demand.contact;
    if (!contact) return;
    wx.setClipboardData({
      data: contact,
      success: () => wx.showToast({ title: '联系方式已复制', icon: 'none' }),
    });
  },

  onBack() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack();
    } else {
      wx.switchTab({ url: '/pages/service-plaza/service-plaza' });
    }
  },
});
