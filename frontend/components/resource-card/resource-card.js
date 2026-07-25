/**
 * 道藏天阁资源卡片组件
 * components/resource-card/resource-card.js
 */
Component({
  properties: {
    resource: { type: Object, value: null },
    compact: { type: Boolean, value: false },
  },

  methods: {
    onTap() {
      const { id } = this.data.resource;
      if (id) {
        wx.navigateTo({
          url: `/subpackages/jingzang/resource-detail/resource-detail?id=${id}`,
        });
      }
    },
  },
});
