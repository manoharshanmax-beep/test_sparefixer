from marshmallow import Schema, fields, validate


class SignupSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))
    phone = fields.String(required=False, allow_none=True)


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class OrderCreateSchema(Schema):
    part_id = fields.String(required=True)
    shop_id = fields.String(required=True)
    quantity = fields.Integer(required=False, load_default=1, validate=validate.Range(min=1, max=50))


class PartSearchSchema(Schema):
    q = fields.String(required=False, allow_none=True)
    vehicle_type = fields.String(required=False, allow_none=True)
    category = fields.String(required=False, allow_none=True)
    model_id = fields.Integer(required=False, allow_none=True)
    min_price = fields.Float(required=False, allow_none=True)
    max_price = fields.Float(required=False, allow_none=True)
    page = fields.Integer(required=False, load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(required=False, load_default=20, validate=validate.Range(min=1, max=100))
