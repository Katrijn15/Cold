import os
import logging
from logging.config import dictConfig
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PREFIX = os.getenv('BOT_PREFIX')

LOGGING_CONFIG = {
    'version': 1,
    'disabled_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '%(levelname)-10s - %(asctime) - %(module)-15s : %(message)s'
        },

        'standard': {
            'format': '%(levelname)-10s - %(name)-15s : %(message)s'
        }
    },
    
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'console2': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'C:/Users/katri/Desktop/Cold/logs/info.log',
            'mode': 'w',
            'formatter': 'verbose'
        }
    },

    'loggers': {
        'bot': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'discord': {
            'handlers': ['console2', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

dictConfig(LOGGING_CONFIG)
