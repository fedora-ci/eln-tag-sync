#!groovy

pipeline {
    agent { label 'eln' }

    options {
        buildDiscarder(
            logRotator(
                numToKeepStr: '50',
                artifactNumToKeepStr: '50'
            )
        )
        disableConcurrentBuilds()
    }

    // triggers {
	//     cron('H * * * *')
    // }

    parameters {
        string(
            name: 'SOURCE_TAG',
            defaultValue: 'f34',
            trim: true,
            description: 'Source tag.'
        )
        string(
            name: 'DESTINATION_TAG',
            defaultValue: 'f34-cr-eln',
            trim: true,
            description: 'Destination tag.'
        )
    }

    stages {
        stage('Sync Tags') {
            environment {
                KOJI_KEYTAB = credentials('fedora-keytab')
            }

            steps {
                sh "$WORKSPACE/eln-tag-sync.py --srctag ${params.SOURCE_TAG} --desttag ${params.DESTINATION_TAG}"
            }
        }
    }
}
