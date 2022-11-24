# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from time import strftime

from odoo import models, fields, _, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipping_acct_nuances = fields.Text(string="Shipping Acct Nuances", related="partner_id.shipping_acct_nuances")
    transfer_nuances = fields.Text(string="Transfer Nuances", related="partner_id.transfer_nuances")
    future_ship_nuances = fields.Text(string="Future Ship Nuances", related="partner_id.future_ship_nuances")
    minimums_nuances = fields.Text(string="Minimums Nuances", related="partner_id.minimums_nuances")
    shipping_nuances = fields.Text(string="Shipping Nuances", related="partner_id.shipping_nuances")
    rush_processing_nuances = fields.Text(string="Rush Shipping Nuances", related="partner_id.rush_processing_nuances")
    frieght_nuances = fields.Text(string="Freight Nuances", related="partner_id.frieght_nuances")
    pre_approval_nuances = fields.Text(string="Pre Approval Nuances", related="partner_id.pre_approval_nuances")
    author_event_shipping_naunces = fields.Text(string="Author Event Shipping Nuances",
                                                related="partner_id.author_event_shipping_naunces")
    applicable_tracking_ids = fields.Many2many('purchase.tracking', compute="_compute_applicable_tracking_ids")
    purchase_tracking_id = fields.Many2one('purchase.tracking', "Purchase Tracking", copy=False)

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        for picking_id in self:
            # Update status as 'received' if shipment  is done
            if vals.get('date_done') and picking_id.purchase_tracking_id:
                picking_id.purchase_tracking_id.status = 'received'
        return res

    def _compute_applicable_tracking_ids(self):
        for picking in self:
            applicable_tracking_ids = picking.move_lines.mapped('purchase_line_id').mapped(
                'order_id').purchase_tracking_ids
            picking.applicable_tracking_ids = applicable_tracking_ids.filtered(lambda x: x.status != 'received')

    def backorder_run_scheduler(self):

        today_datetime = datetime.now()
        today_date = today_datetime.date()
        next_day_start = (today_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        next_day_end = (today_date + timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
        next_week_start = (today_date + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        next_week_end = (today_date + timedelta(days=7)).strftime("%Y-%m-%d 23:59:59")

        day_backorder_ids = self.env['stock.picking'].search([('backorder_id', '!=', False),
                                                              ('picking_type_code', '=', 'incoming'),
                                                              ('state', 'not in', ('done', 'cancel')),
                                                              ('scheduled_date', '>=', next_day_start),
                                                              ('scheduled_date', '<=', next_day_end)])
        week_backorder_ids = self.env['stock.picking'].search([('backorder_id', '!=', False),
                                                               ('picking_type_code', '=', 'incoming'),
                                                               ('state', 'not in', ('done', 'cancel')),
                                                               ('scheduled_date', '>=', next_week_start),
                                                               ('scheduled_date', '<=', next_week_end)])
        template_one = self.env.ref('bista_purchase.email_template_purchase_reciept_first_reminder')
        template_second = self.env.ref('bista_purchase.email_template_purchase_reciept_second_reminder')

        if day_backorder_ids:
            for rec in day_backorder_ids:
                template_one.send_mail(rec.id, force_send=True)
        if week_backorder_ids:
            for record in week_backorder_ids:
                template_second.send_mail(record.id, force_send=True)

    def backorder_run_deadline(self):
        current_datetime = datetime.now()
        current_date = current_datetime.date()
        one_day_bo_ids = self.env['stock.picking'].search([('backorder_id', '!=', False),
                                                           ('picking_type_code', '=', 'incoming'),
                                                           ('state', 'in', ('waiting', 'confirmed', 'assigned')),
                                                           ('date_deadline', '<', current_date)])
        template_deadline = self.env.ref('bista_purchase.email_template_purchase_reciept_deadline_reminder')
        if one_day_bo_ids:
            for temp in one_day_bo_ids:
                template_deadline.send_mail(temp.id, force_send=True)

    def compute_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(self.id) + '&model=stock.picking&view_type=form'
        return url