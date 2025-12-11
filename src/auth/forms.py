from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Regexp

class EstudanteForm(FlaskForm):
    class Meta:
        csrf = False # O CSRF é tratado no form pai ou globalmente

    # O nome precisa bater com o que o JS gera ou o JS precisa mudar.
    # O JS atual gera: estudantes[{index}][nome]
    # O WTForms espera: estudantes-{index}-nome
    # Vamos manter o HTML como está e usar um custom parser ou ajustar o JS?
    # O User pediu para "manter o CSS impecável", mas podemos ajustar o JS.
    
    nome = StringField('Nome', validators=[
        DataRequired(message="Nome é obrigatório"),
        Length(min=3, max=100, message="Nome deve ter entre 3 e 100 caracteres"),
        Regexp(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s\.]+$', message="Nome deve conter apenas letras")
    ])
    
    segmento = SelectField('Segmento', choices=[
        ('EI', 'Educação Infantil'), 
        ('AI', 'Anos Iniciais'), 
        ('AF', 'Anos Finais'), 
        ('EM', 'Ensino Médio')
    ], validators=[DataRequired()])
    
    serie = SelectField('Série', validators=[DataRequired()])
    
    # Periodo e Turma são dependentes, validamos se estão preenchidos
    periodo = SelectField('Período', validators=[DataRequired()])
    turma = SelectField('Turma', validators=[DataRequired()])
    
    integral = BooleanField('Integral')

class CadastroAlunosForm(FlaskForm):
    # FieldList para gerenciar múltiplos alunos
    estudantes = FieldList(FormField(EstudanteForm), min_entries=1)
