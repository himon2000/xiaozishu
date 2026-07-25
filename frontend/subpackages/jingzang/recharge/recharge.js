// 灵石充值页面
const api = require('../api');

Page({
  data: {
    balance: 0,
    packages: [
      { id: 1, stones: 100,   price: 1,   bonus: 0   },
      { id: 2, stones: 500,   price: 5,   bonus: 10  },
      { id: 3, stones: 1000,  price: 10,  bonus: 30  },
      { id: 4, stones: 2000,  price: 20,  bonus: 80  },
      { id: 5, stones: 5000,  price: 50,  bonus: 200 },
      { id: 6, stones: 10000, price: 100, bonus: 500 },
    ],
    selectedPackage: null,
    customAmount: '',
    totalPrice: 0,
    totalStones: 0,
    agreed: false,
  },

  onLoad: function () {
    this.loadBalance();
  },

  onShow: function () {
    this.loadBalance();
  },

  loadBalance: function () {
    var self = this;
    api.get('/auth/me').then(function (res) {
      if (res && res.spirit_stones !== undefined) {
        self.setData({ balance: res.spirit_stones || 0 });
      }
    }).catch(function () {});
  },

  onSelectPackage: function (e) {
    var id = e.currentTarget.dataset.id;
    var pkg = this.data.packages.find(function (p) { return p.id === id; });
    if (!pkg) return;
    this.setData({
      selectedPackage: id,
      customAmount: '',
      totalPrice: pkg.price,
      totalStones: pkg.stones + pkg.bonus,
      agreed: false,
    });
  },

  onCustomInput: function (e) {
    var val = e.detail.value;
    var amount = parseFloat(val) || 0;
    this.setData({
      selectedPackage: null,
      customAmount: val,
      totalPrice: amount,
      totalStones: Math.floor(amount * 100),
      agreed: false,
    });
  },

  onAgreementChange: function (e) {
    var vals = e.detail.value || [];
    this.setData({ agreed: vals.indexOf('agree') >= 0 });
  },

  onViewAgreement: function () {
    wx.showModal({
      title: '灵石充值协议',
      content: '1. 灵石是小紫薯平台的虚拟货币，可用于购买服务和悬赏。\n2. 充值比例：1元人民币=100灵石（赠品除外）。\n3. 灵石不可提现，不可转让。\n4. 购买服务后，灵石将直接支付给服务者。\n5. 如有退款问题，请联系客服处理。',
      showCancel: false,
      confirmText: '我已知晓',
    });
  },

  onRecharge: function () {
    var self = this;
    var totalPrice = this.data.totalPrice;
    var totalStones = this.data.totalStones;
    var agreed = this.data.agreed;
    if (totalPrice <= 0) {
      wx.showToast({ title: '请选择套餐或输入金额', icon: 'none' });
      return;
    }
    if (!agreed) {
      wx.showToast({ title: '请先阅读并同意充值协议', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '正在处理...' });

    api.post('/wallet/recharge', { price: totalPrice, stones: totalStones }).then(function (res) {
      if (res && res.success) {
        return api.post('/wallet/recharge/callback', {
          order_id: res.order_id,
          status: 'success',
          stones: totalStones,
        });
      } else {
        throw new Error((res && res.message) ? res.message : '创建订单失败');
      }
    }).then(function (callbackRes) {
      var creditedStones = (callbackRes && callbackRes.credited_stones) || totalStones;
      wx.hideLoading();
      wx.showModal({
        title: '充值成功',
        content: '恭喜！' + creditedStones + '颗灵石已到账！',
        showCancel: false,
        success: function () {
          self.setData({
            balance: (callbackRes && callbackRes.spirit_stones) || (self.data.balance + creditedStones),
            selectedPackage: null,
            customAmount: '',
            totalPrice: 0,
            totalStones: 0,
            agreed: false,
          });
        },
      });
    }).catch(function (err) {
      wx.hideLoading();
      var msg = (err && err.message) ? err.message : '请检查网络后重试';
      wx.showModal({
        title: '充值失败',
        content: '很抱歉，充值未成功。\n' + msg + '\n如多次失败请联系客服。',
        showCancel: false,
        confirmText: '我知道了',
      });
    });
  },
});
