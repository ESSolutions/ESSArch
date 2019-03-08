import os
import shutil
import tempfile

from django.test import TestCase

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.csv import CSVValidator


class CSVValidatorTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def create_file(self, data, filename):
        path = os.path.join(self.datadir, filename)
        with open(path, 'w') as f:
            f.write(data)

        return path

    def test_valid(self):
        csv = self.create_file("""\
"Year", "Score", "Title"
1968,  86, "Greetings"
1970,  17, "Bloody Mama"
1970,  73, "Hi Mom!"
1971,  40, "Born to Win"
1973,  98, "Mean Streets"
1973,  88, "Bang the Drum Slowly"
1974,  97, "The Godfather Part II"
1976,  41, "The Last Tycoon"
1976,  99, "Taxi Driver"
""", 'foo.csv')

        validator = CSVValidator(options={'column_number': 3})
        validator.validate(csv)

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_incorrect_delimiter(self):
        csv = self.create_file("""\
"Year", "Score", "Title"
1968,  86, "Greetings"
1970,  17, "Bloody Mama"
1970,  73, "Hi Mom!"
1971;  40; "Born to Win"
1973,  98, "Mean Streets"
1973,  88, "Bang the Drum Slowly"
1974;  97, "The Godfather Part II"
1976,  41, "The Last Tycoon"
1976,  99, "Taxi Driver"
""", 'foo.csv')

        validator = CSVValidator(options={'column_number': 3})

        with self.assertRaises(ValidationError):
            validator.validate(csv)

        self.assertEqual(Validation.objects.count(), 2)

        expected_msg = 'Wrong delimiter for post '
        self.assertEqual(Validation.objects.filter(message__startswith=expected_msg).count(), 2)

    def test_incorrect_column_count(self):
        csv = self.create_file("""\
"Year", "Score", "Title"
1968,  86, "Greetings"
1970,  17, "Bloody Mama"
1970,  73, "Hi Mom!"
1971,  40, "Born to Win"
1973, "Mean Streets"
1973,  88, "Bang the Drum Slowly"
1974,  97, "The Godfather Part II"
1976,  41, "The Last Tycoon"
1976,  99, "Taxi Driver"
""", 'foo.csv')

        validator = CSVValidator(options={'column_number': 3})

        with self.assertRaises(ValidationError):
            validator.validate(csv)

        self.assertEqual(Validation.objects.count(), 1)

        expected_msg = 'Wrong delimiter for post '  # same thing as wrong column count
        self.assertEqual(Validation.objects.filter(message__startswith=expected_msg).count(), 1)

    def test_missing_line_break(self):
        csv = self.create_file("""\
"Year", "Score", "Title"
1968,  86, "Greetings"
1970,  17, "Bloody Mama"
1970,  73, "Hi Mom!"
1971,  40, "Born to Win"
1973,  98, "Mean Streets"
1973,  88, "Bang the Drum Slowly"
1974,  97, "The Godfather Part II"
1976,  41, "The Last Tycoon"
1976,  99, "Taxi Driver""", 'foo.csv')

        validator = CSVValidator(options={'column_number': 3})

        with self.assertRaises(ValidationError):
            validator.validate(csv)

        self.assertEqual(Validation.objects.count(), 1)

        expected_msg = 'Missing line break for post '
        self.assertEqual(Validation.objects.filter(message__startswith=expected_msg).count(), 1)
