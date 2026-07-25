/**
 * 订单列表
 * 路径：pages/order-list/order-list
 */
const { get } = require('../../utils/request');

const STATUS_CONFIG = {
  pending_payment:  { label: '待付灵石', sub: '(待支付)', color: '#ffa502' },
  paid:             { label: '已付灵石', sub: '(已支付)', color: '#00d4ff' },
  assigned:         { label: '已接单', sub: '(已接单)', color: '#00d4ff' },
  in_progress:      { label: '修炼中', sub: '(进行中)', color: '#cc44ff' },
  pending_confirm:   { label: '待验收', sub: '(待确认)', color: '#ffa502' },
  completed:        { label: '已完成', sub: '(已完成)', color: '#2ed573' },
  dispute:          { label: '纠纷中', sub: '(纠纷中)', color: '#ff4757' },
  cancelled:        { label: '已废弃', sub: '(已取消)', color: '#999' },
};

Page({
  data: {
    role: 'seeker',
    statusFilter: '',
    orders: [],
    page: 1,
    loading: false,
    noMore: false,
    tabs: [
      { key: 'seeker', label: '👤 求道者视角' },
      { key: 'provider', label: '📜 传法者视角' },
    ],
  },

  onLoad(options) {
    if (options.role) {
      this.setData({ role: options.role });
    }
    this.loadOrders(true);
  },

  async loadOrders(reset = false) {
    if (this.data.loading) return;
    if (reset) {
      this.setData({ page: 1, orders: [], noMore: false });
    }
    if (this.data.noMore) return;

    this.setData({ loading: true });
    try {
      const res = await get('/orders', {
        role: this.data.role,
        status_filter: this.data.statusFilter,
        page: this.data.page,
        page_size: 20,
      }).catch(e => {
        console.error('加载订单列表失败', e);
        return { orders: reset ? [] : this.data.orders, total: this.data.orders.length };
      });
      if (!res) { this.setData({ loading: false }); return; }
      const list = reset ? (res.orders || []) : [...this.data.orders, ...(res.orders || [])];
      this.setData({
        orders: list,
        page: this.data.page + 1,
        noMore: list.length >= (res.total || 0),
        loading: false,
      });
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  onReachBottom() {
    this.loadOrders();
  },

  onTabChange(e) {
    const { key } = e.currentTarget.dataset;
    this.setData({ role: key });
    this.loadOrders(true);
  },

  onOrderTap(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/order-detail/order-detail?order_id=${id}` });
  },

  onGoHome() {
    wx.switchTab({ url: '/pages/home/home' });
  },
});
