FROM public.ecr.aws/lambda/python:3.12

COPY src/requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements.txt

COPY src/lambda_function.py ${LAMBDA_TASK_ROOT}

CMD [ "lambda_function.lambda_handler" ]
