from datetime import date
from odoo import api,fields,models,Command
from odoo.exceptions import AccessError,UserError,ValidationError
from ..common import guard

class Contract(models.Model):
    _name='franchise.contract'
    _description='Fictional Headquarters Franchise Contract'
    _inherit=['mail.thread','mail.activity.mixin']
    _check_company_auto=True
    name=fields.Char(required=True)
    code=fields.Char(required=True)
    company_id=fields.Many2one('res.company',required=True,default=lambda s:s.env.company)
    partner_id=fields.Many2one('res.partner',required=True,check_company=True)
    region=fields.Selection([('north','North'),('south','South'),('east','East'),('west','West')],required=True)
    administrator_id=fields.Many2one('res.users',default=lambda s:s.env.user)
    start_date=fields.Date(required=True,default=fields.Date.context_today)
    end_date=fields.Date()
    active=fields.Boolean(default=True)
    state=fields.Selection([('draft','Draft'),('active','Active'),('suspended','Suspended'),('closed','Closed')],default='draft',tracking=True)
    currency_id=fields.Many2one('res.currency',required=True,default=lambda s:s.env.company.currency_id)
    fee_ids=fields.One2many('franchise.fee.line','contract_id')
    note=fields.Text()
    _sql_constraints=[('code_unique','unique(company_id,code)','Franchise identifier must be unique.')]
    @api.constrains('start_date','end_date')
    def _dates(self):
        if any(c.end_date and c.end_date<c.start_date for c in self): raise ValidationError('Invalid contract date range.')
    def action_bill_current(self):
        guard(self,'franchise_operations.group_accounts')
        for contract in self:
            period=fields.Date.context_today(contract).replace(day=1)
            contract._bill(period)
        return True
    def _bill(self,period):
        self.ensure_one()
        guard(self,'franchise_operations.group_accounts',operation='read')
        if self.state!='active' or not self.active or self.start_date>period or (self.end_date and self.end_date<period):
            return self.env['franchise.billing']
        existing=self.env['franchise.billing'].search([('contract_id','=',self.id),('period','=',period)],limit=1)
        if existing: return existing
        if not self.fee_ids: raise UserError('Configure fictional recurring fee lines before billing.')
        invoice=self.env['account.move'].with_company(self.company_id).create({'move_type':'out_invoice',
            'company_id':self.company_id.id,'partner_id':self.partner_id.id,'currency_id':self.currency_id.id,
            'franchise_id':self.id,'invoice_date':period,'invoice_origin':self.code+' '+str(period),
            'invoice_line_ids':[Command.create({'product_id':line.product_id.id,'name':line.name,
                'quantity':1,'price_unit':line.amount,'discount':line.discount_percent}) for line in self.fee_ids]})
        return self.env['franchise.billing'].create({'contract_id':self.id,'period':period,'invoice_id':invoice.id})
    @api.model
    def _cron_bill(self):
        today=fields.Date.context_today(self).replace(day=1)
        self.search([('state','=','active'),('active','=',True)]).mapped('id')
        for contract in self.search([('state','=','active'),('active','=',True)]): contract._bill(today)
    @api.model
    def _seed_demo(self):
        for i in range(1,81):
            code='DEMO-%03d'%i
            if self.search_count([('company_id','=',self.env.company.id),('code','=',code)]): continue
            partner=self.env['res.partner'].create({'name':'Fictional Campus Operator %03d'%i,'email':'campus%03d@example.invalid'%i,'company_id':self.env.company.id})
            product=self.env.ref('franchise_operations.monthly_fee')
            self.create({'name':'Fictional Campus %03d'%i,'code':code,'partner_id':partner.id,
                'region':['north','south','east','west'][(i-1)%4],'start_date':date(2026,1,1),'state':'active',
                'fee_ids':[Command.create({'name':'Fictional monthly administration fee','product_id':product.id,'amount':250})]})

class Fee(models.Model):
    _name='franchise.fee.line'
    _description='Recurring Franchise Fee Definition'
    contract_id=fields.Many2one('franchise.contract',required=True,ondelete='cascade')
    company_id=fields.Many2one(related='contract_id.company_id',store=True)
    currency_id=fields.Many2one(related='contract_id.currency_id')
    name=fields.Char(required=True)
    product_id=fields.Many2one('product.product',required=True)
    amount=fields.Monetary(required=True)
    discount_percent=fields.Float(default=0)
    @api.constrains('amount','discount_percent')
    def _valid(self):
        if any(f.amount<0 or not 0<=f.discount_percent<=100 for f in self): raise ValidationError('Invalid fee amount or discount.')

class Billing(models.Model):
    _name='franchise.billing'
    _description='Idempotent Monthly Franchise Invoice'
    contract_id=fields.Many2one('franchise.contract',required=True,ondelete='restrict')
    company_id=fields.Many2one(related='contract_id.company_id',store=True)
    period=fields.Date(required=True)
    invoice_id=fields.Many2one('account.move',required=True,ondelete='restrict')
    currency_id=fields.Many2one(related='invoice_id.currency_id')
    total=fields.Monetary(related='invoice_id.amount_total')
    residual=fields.Monetary(related='invoice_id.amount_residual')
    payment_state=fields.Selection(related='invoice_id.payment_state')
    _sql_constraints=[('monthly_unique','unique(contract_id,period)','Monthly invoice already exists for this franchise.')]
    def write(self,vals): raise AccessError('Billing references are immutable; correct the accounting document through a credit note.')
    @api.constrains('period')
    def _valid(self):
        if any(r.period.day!=1 for r in self): raise ValidationError('Billing period must be the first of its month.')

class Move(models.Model):
    _inherit='account.move'
    franchise_id=fields.Many2one('franchise.contract',copy=True,check_company=True,index=True)

class Dashboard(models.Model):
    _name='franchise.dashboard'
    _description='Headquarters Receivables Dashboard'
    name=fields.Char(default='Fictional Headquarters Summary',required=True)
    company_id=fields.Many2one('res.company',required=True,default=lambda s:s.env.company)
    month=fields.Date(default=lambda s:fields.Date.context_today(s).replace(day=1),required=True)
    currency_id=fields.Many2one(related='company_id.currency_id')
    campus_count=fields.Integer(compute='_compute_summary')
    active_count=fields.Integer(compute='_compute_summary')
    billed=fields.Monetary(compute='_compute_summary')
    collected=fields.Monetary(compute='_compute_summary')
    outstanding=fields.Monetary(compute='_compute_summary')
    overdue=fields.Monetary(compute='_compute_summary')
    regions=fields.Json(compute='_compute_summary')
    def _compute_summary(self):
        for board in self:
            contracts=self.env['franchise.contract'].with_context(active_test=False).search([('company_id','=',board.company_id.id)])
            board.campus_count=len(contracts);board.active_count=len(contracts.filtered(lambda c:c.active and c.state=='active'))
            month=board.month.replace(day=1)
            end=date(month.year+1,1,1) if month.month==12 else date(month.year,month.month+1,1)
            all_moves=self.env['account.move'].search([('company_id','=',board.company_id.id),('franchise_id','!=',False),('state','=','posted'),('move_type','in',['out_invoice','out_refund'])])
            moves=all_moves.filtered(lambda m:m.invoice_date and month<=m.invoice_date<end)
            board.billed=sum(moves.mapped('amount_total_signed'))
            board.collected=sum(m.amount_total_signed-m.amount_residual_signed for m in moves)
            board.outstanding=sum(all_moves.mapped('amount_residual_signed'))
            board.overdue=sum(m.amount_residual_signed for m in all_moves if m.invoice_date_due and m.invoice_date_due<fields.Date.context_today(board))
            board.regions={region:{'billed':sum(m.amount_total_signed for m in moves if m.franchise_id.region==region),
                                   'outstanding':sum(m.amount_residual_signed for m in all_moves if m.franchise_id.region==region)} for region in ('north','south','east','west')}
